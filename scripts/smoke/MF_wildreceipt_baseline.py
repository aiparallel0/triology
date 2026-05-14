"""MF: sigma vs softmax baseline on WildReceipt (labeled-amounts, encoder-only).

v2 fix: previous version skipped all 472 records because the dataset's text/bbox
fields didn't match the guessed names. v2 introspects the schema and handles
multiple loaders + field variants robustly.

Tests whether softmax-aggregation (geo-mean max-prob over Total_value tokens)
dominates sigma on WildReceipt where F reports sigma_precision=0.95 @ 45% coverage.

Runtime ~30s on RTX 4090 once schema is matched.
"""
import gc, json, os, re, sys, time
from collections import Counter
from io import BytesIO
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from datasets import load_dataset
from transformers import AutoProcessor, LayoutLMv3ForTokenClassification

CKPT = "Theivaprakasham/layoutlmv3-finetuned-wildreceipt"
F_OUT = Path("runs/F_layoutlmv3_on_wildreceipt.json")
OUT = Path("runs/MF_wildreceipt_baseline.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
BATCH = int(os.environ.get("LAYOUTLM_BATCH", "16"))

TOTAL_VALUE_ID = 23  # WildReceipt label id


def parse_money(s):
    if s is None: return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", "").replace("$", ""))
    return float(m.group()) if m else None


def load_image_field(v):
    """Load an image from a PIL object, path string, dict, or bytes."""
    if v is None: return None
    if hasattr(v, "convert"): return v.convert("RGB")
    if isinstance(v, dict):
        if v.get("bytes"):
            return Image.open(BytesIO(v["bytes"])).convert("RGB")
        if v.get("path"):
            try: return Image.open(v["path"]).convert("RGB")
            except Exception: return None
    if isinstance(v, str):
        try: return Image.open(v).convert("RGB")
        except Exception: return None
    if isinstance(v, (bytes, bytearray)):
        return Image.open(BytesIO(v)).convert("RGB")
    return None


def normalize_bbox(box, w, h):
    """Convert pixel-space bbox to [0,1000] for LayoutLMv3."""
    if not box or len(box) < 4: return [0, 0, 0, 0]
    x0, y0, x1, y1 = box[:4]
    return [
        int(1000 * max(0, min(1, x0 / max(1, w)))),
        int(1000 * max(0, min(1, y0 / max(1, h)))),
        int(1000 * max(0, min(1, x1 / max(1, w)))),
        int(1000 * max(0, min(1, y1 / max(1, h)))),
    ]


def extract_fields(ex):
    """Schema-flex: try multiple field names. Returns (img, words, boxes, w, h)."""
    img = (load_image_field(ex.get("image")) or
           load_image_field(ex.get("img")) or
           load_image_field(ex.get("image_path")))
    if img is None:
        return None, None, None, None, None
    w, h = img.size
    words = (ex.get("tokens") or ex.get("words") or
             ex.get("text") or ex.get("texts") or [])
    boxes = (ex.get("bboxes") or ex.get("boxes") or
             ex.get("bbox") or ex.get("normalized_bboxes") or [])
    return img, words, boxes, w, h


def try_load():
    """Try multiple WildReceipt loaders in order of preference."""
    candidates = [
        "Theivaprakasham/wildreceipt",
        "jinhybr/WildReceipt",
    ]
    for ref in candidates:
        try:
            ds = load_dataset(ref, split="test", trust_remote_code=True)
            print(f"  loaded {ref} n={len(ds)}; columns: {ds.column_names}")
            return ds, ref
        except Exception as e:
            print(f"  miss {ref}: {type(e).__name__}: {str(e)[:200]}")
    return None, None


def main():
    t0 = time.time()
    f_in_T, f_correct = {}, {}
    if F_OUT.exists():
        f = json.loads(F_OUT.read_text())
        for r in f.get("results", []):
            rid = r.get("id")
            f_in_T[rid] = r.get("in_T", False)
            f_correct[rid] = r.get("correct", False)
        print(f"  loaded F's {len(f_in_T)} sigma_accept flags")

    print(f"Loading {CKPT}...")
    processor = AutoProcessor.from_pretrained(CKPT, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(CKPT).to("cuda").eval()

    ds, ref = try_load()
    if ds is None:
        OUT.write_text(json.dumps({"available": False, "reason": "no WildReceipt loader reachable"}, indent=2))
        return

    # Diagnostic: dump first record's schema
    first = ds[0]
    schema = {k: (type(v).__name__ if not isinstance(v, (int, float, bool, type(None)))
                  else (str(v)[:60] if isinstance(v, str) else v))
              for k, v in first.items()}
    print(f"  first-record schema: {json.dumps(schema, default=str)[:300]}")

    results = []
    skip_reasons = Counter()
    t1 = time.time()
    for i in range(0, len(ds), BATCH):
        batch_idx = list(range(i, min(i + BATCH, len(ds))))
        batch = [ds[j] for j in batch_idx]

        images, words_list, boxes_list = [], [], []
        keep_idx = []
        for ex_idx, ex in zip(batch_idx, batch):
            img, words, boxes, w, h = extract_fields(ex)
            if img is None:
                skip_reasons["no_image"] += 1; continue
            if not words:
                skip_reasons["no_words"] += 1; continue
            if not boxes:
                skip_reasons["no_boxes"] += 1; continue
            if len(words) != len(boxes):
                skip_reasons["words_boxes_mismatch"] += 1; continue
            # Normalize bboxes to [0, 1000] if they appear to be in pixel space
            try:
                if any(any(c > 1000 for c in b[:4]) for b in boxes):
                    boxes = [normalize_bbox(b, w, h) for b in boxes]
                else:
                    # Already normalized or 0-1 range
                    boxes = [list(b[:4]) for b in boxes]
                # Truncate to 512 tokens for LayoutLMv3 sequence length
                if len(words) > 510:
                    words = words[:510]; boxes = boxes[:510]
                # Ensure words are strings
                words = [str(w) for w in words]
            except Exception as e:
                skip_reasons[f"bbox_norm_fail"] += 1; continue
            images.append(img); words_list.append(words); boxes_list.append(boxes)
            keep_idx.append(ex_idx)

        if not images:
            if i == 0:
                print(f"  WARN: first batch yielded 0 valid examples; skip_reasons={dict(skip_reasons)}")
            continue

        try:
            enc = processor(images=images, text=words_list, boxes=boxes_list,
                            return_tensors="pt", padding=True, truncation=True).to("cuda")
        except Exception as e:
            print(f"  batch encode fail: {type(e).__name__}: {str(e)[:200]}")
            skip_reasons["encode_fail"] += len(images)
            continue

        with torch.inference_mode():
            logits = model(**enc).logits
        probs = torch.softmax(logits.float(), dim=-1)
        preds = logits.argmax(dim=-1)

        for b, ex_idx in enumerate(keep_idx):
            mask = preds[b] == TOTAL_VALUE_ID
            if mask.sum().item() == 0:
                sm = None
            else:
                max_probs = probs[b].gather(-1, preds[b].unsqueeze(-1)).squeeze(-1)
                total_probs = max_probs[mask].cpu().tolist()
                log_ps = [np.log(max(p, 1e-12)) for p in total_probs]
                sm = float(np.exp(np.mean(log_ps))) if log_ps else None

            results.append({
                "id": ex_idx,
                "softmax_score": sm,
                "correct": f_correct.get(ex_idx, False),
                "sigma_accept": f_in_T.get(ex_idx, False),
            })
        if (i // BATCH + 1) % 5 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {min(i+BATCH, len(ds))}/{len(ds)} elapsed={time.time()-t1:.0f}s")

    print(f"  skip_reasons: {dict(skip_reasons)}")

    n = max(1, len(results))
    correct_all = sum(r["correct"] for r in results)
    sigma_accept = [r for r in results if r["sigma_accept"]]
    sigma_cov = len(sigma_accept) / n
    sigma_correct = sum(r["correct"] for r in sigma_accept)
    sigma_prec = sigma_correct / max(1, len(sigma_accept))

    scored = [r for r in results if r["softmax_score"] is not None]
    scored.sort(key=lambda r: -r["softmax_score"])
    k_match = len(sigma_accept)
    softmax_match = scored[:k_match] if k_match else []
    softmax_correct_matched = sum(r["correct"] for r in softmax_match)
    softmax_prec_matched = softmax_correct_matched / max(1, len(softmax_match))

    sweep = []
    for frac in (0.05, 0.10, 0.20, 0.30, 0.40, 0.45, 0.50, 0.70, 0.85, 1.0):
        k = int(round(frac * len(scored)))
        if k == 0 or k > len(scored): continue
        topk = scored[:k]
        c = sum(r["correct"] for r in topk)
        sweep.append({"k": k, "coverage": k / n, "precision": c / max(1, k)})

    sigma_ids = {r["id"] for r in sigma_accept}
    softmax_ids = {r["id"] for r in softmax_match}
    intersect = sigma_ids & softmax_ids
    union = sigma_ids | softmax_ids
    def prec_of(ids):
        sub = [r for r in results if r["id"] in ids]
        if not sub: return None
        return sum(r["correct"] for r in sub) / len(sub)

    summary = {
        "corpus": "WildReceipt test (labeled-amounts, encoder-only)",
        "ckpt": CKPT,
        "loader": ref,
        "n": len(results),
        "wall_sec": round(time.time() - t0, 1),
        "skip_reasons": dict(skip_reasons),
        "base_rate_F1": correct_all / n,
        "sigma": {
            "coverage": sigma_cov, "precision": sigma_prec,
            "n_accepted": len(sigma_accept), "n_correct": sigma_correct,
        },
        "softmax_matched_coverage": {
            "coverage": k_match / n, "precision": softmax_prec_matched,
            "n_accepted": len(softmax_match), "n_correct": softmax_correct_matched,
        },
        "softmax_threshold_sweep": sweep,
        "orthogonality": {
            "|sigma|": len(sigma_ids), "|softmax|": len(softmax_ids),
            "|union|": len(union), "|intersect|": len(intersect),
            "intersect_precision": prec_of(intersect),
            "union_precision": prec_of(union),
            "sigma_only_precision": prec_of(sigma_ids - softmax_ids),
            "softmax_only_precision": prec_of(softmax_ids - sigma_ids),
        },
        "verdict_hook": (
            "Per CORD's result (MB: sigma 0.982 vs softmax 0.927, sigma_only_precision=1.0), "
            "expect sigma to win on WildReceipt too if the labeled-amounts regime hypothesis holds. "
            "If softmax wins here, the regime distinction is corpus-specific to CORD only."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
