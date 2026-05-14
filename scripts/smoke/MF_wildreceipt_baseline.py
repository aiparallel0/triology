"""MF: sigma vs softmax baseline on WildReceipt (labeled-amounts, encoder-only).

Tests whether softmax-aggregation (mean max-prob across predicted-as-Total tokens)
dominates sigma on WildReceipt where F reports sigma_precision=0.95 @ 45% coverage.
Mirror of MB but for LayoutLMv3 token classification.

If softmax also beats sigma here, the regime distinction is dead.

Runtime ~30s on RTX 4090.
"""
import gc, json, os, re, sys, time
from pathlib import Path

import numpy as np
import torch
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


def main():
    t0 = time.time()
    f_in_T, f_correct = {}, {}
    if F_OUT.exists():
        f = json.loads(F_OUT.read_text())
        for r in f.get("results", []):
            rid = r.get("id")
            f_in_T[rid] = r.get("in_T", False)
            f_correct[rid] = r.get("correct", False)
    else:
        print("WARN: F's runs/F_layoutlmv3_on_wildreceipt.json not found")

    print(f"Loading {CKPT}...")
    processor = AutoProcessor.from_pretrained(CKPT, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(CKPT).to("cuda").eval()

    try:
        ds = load_dataset("jinhybr/WildReceipt", split="test", trust_remote_code=True)
    except Exception:
        ds = load_dataset("Theivaprakasham/wildreceipt", split="test", trust_remote_code=True)
    print(f"WildReceipt test n={len(ds)}")

    results = []
    t1 = time.time()
    for i in range(0, len(ds), BATCH):
        batch_idx = list(range(i, min(i + BATCH, len(ds))))
        batch = [ds[j] for j in batch_idx]

        images, words_list, boxes_list = [], [], []
        keep_idx = []
        for ex_idx, ex in zip(batch_idx, batch):
            try:
                img = ex.get("image")
                if hasattr(img, "convert"): img = img.convert("RGB")
                words = ex.get("words") or ex.get("tokens") or []
                boxes = ex.get("bboxes") or ex.get("boxes") or []
                if img is None or not words: continue
                images.append(img); words_list.append(words); boxes_list.append(boxes)
                keep_idx.append(ex_idx)
            except Exception:
                continue
        if not images: continue

        try:
            enc = processor(images=images, text=words_list, boxes=boxes_list,
                            return_tensors="pt", padding=True, truncation=True).to("cuda")
        except Exception as e:
            print(f"  batch encode fail: {e}"); continue

        with torch.inference_mode():
            logits = model(**enc).logits  # [B, L, C]
        probs = torch.softmax(logits.float(), dim=-1)

        preds = logits.argmax(dim=-1)  # [B, L]
        for b, ex_idx in enumerate(keep_idx):
            mask = preds[b] == TOTAL_VALUE_ID
            if mask.sum().item() == 0:
                sm = None
            else:
                max_probs = probs[b].gather(-1, preds[b].unsqueeze(-1)).squeeze(-1)
                # Aggregate confidence: geo-mean of max-probs over Total_value tokens
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
        "n": len(results),
        "wall_sec": round(time.time() - t0, 1),
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
            "Compare sigma.precision vs softmax_matched.precision. If softmax wins here too, "
            "the regime distinction is dead and Paper 1 pivots entirely to orthogonality. "
            "WildReceipt is encoder-only (token classifier), so softmax is aggregated as "
            "geo-mean max-prob over tokens classified as Total_value."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
