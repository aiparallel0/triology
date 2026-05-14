"""LayoutLMv3-WildReceipt on WildReceipt-test → I3 selective prediction (in-distribution).

Third-corpus / third-backbone characterization for Paper 1.
Upstream: Theivaprakasham/layoutlmv3-finetuned-wildreceipt (encoder-only token classifier).
Corpus: WildReceipt test split (n=472).
Verification: I3 uses WildReceipt's labeled Prod_price_value annotations
(no OCR needed — dataset provides per-token text + bbox + class).

With B (DONUT-CORD on CORD) and A v6 (DONUT-SROIE on SROIE), gives a
three-corpus three-backbone sigma characterization — the measured evidence
for the architecture-agnostic claim.

Runtime: ~1.5 min on RTX 4090.
Success: F1_sigma_strict > F1_bare — sigma is a precision gate on a third architecture.
"""
import gc, json, re, time, urllib.request, tarfile
from pathlib import Path

import torch
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification

CKPT = "Theivaprakasham/layoutlmv3-finetuned-wildreceipt"
WILD_URL = "https://download.openmmlab.com/mmocr/data/wildreceipt.tar"
WILD_DIR = Path("data/wildreceipt")
OUT = Path("runs/F_layoutlmv3_on_wildreceipt.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
MAX_MONEY_LINES = 20


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", ".").replace("$", "").replace("RM", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def load_class_list(path):
    cls = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                cls[parts[1]] = int(parts[0])
    return cls


def ensure_wildreceipt():
    if not WILD_DIR.exists():
        print("Downloading WildReceipt (~70 MB)...")
        Path("data").mkdir(exist_ok=True)
        urllib.request.urlretrieve(WILD_URL, "wildreceipt.tar")
        with tarfile.open("wildreceipt.tar") as t: t.extractall("data/")
        Path("wildreceipt.tar").unlink()


def quad_to_xyxy(box):
    xs = [box[0], box[2], box[4], box[6]]
    ys = [box[1], box[3], box[5], box[7]]
    return [min(xs), min(ys), max(xs), max(ys)]


def normalize_box(box, w, h):
    return [
        max(0, min(1000, int(1000 * box[0] / max(1, w)))),
        max(0, min(1000, int(1000 * box[1] / max(1, h)))),
        max(0, min(1000, int(1000 * box[2] / max(1, w)))),
        max(0, min(1000, int(1000 * box[3] / max(1, h)))),
    ]


def row_group(items, y_tol_frac=0.015):
    if not items: return []
    pairs = [(a, (a["box"][1] + a["box"][5]) / 2) for a in items]
    pairs.sort(key=lambda x: x[1])
    img_h = max(a["box"][5] for a in items)
    tol = y_tol_frac * img_h
    rows, cur, last = [], [], None
    for a, y in pairs:
        if last is None or abs(y - last) < tol:
            cur.append(a); last = y if last is None else (last + y) / 2
        else:
            rows.append(cur); cur = [a]; last = y
    if cur: rows.append(cur)
    return rows


def I3_reachable(money_lines, tau, eps=0.02):
    kmin = 1 if abs(tau) > eps else 2
    cents = [int(round(v * 100)) for v in money_lines]
    tau_c = int(round(tau * 100))
    D = {0: 0}
    for v in cents:
        new = dict(D)
        for s, k in D.items():
            ns = s + v
            if ns not in new or new[ns] > k + 1:
                new[ns] = k + 1
        D = new
    return {(s + tau_c) / 100.0 for s, k in D.items() if k >= kmin}


def find_class_idx(id2label, target_substring):
    """Map class-list name to model output id (model labels include BIO prefixes)."""
    for idx, name in id2label.items():
        if target_substring in name:
            return idx
    return None


def main():
    ensure_wildreceipt()
    cls = load_class_list(WILD_DIR / "class_list.txt")
    TOT_ID, TAX_ID, PRC_ID = cls["Total_value"], cls["Tax_value"], cls["Prod_price_value"]
    print(f"Loading {CKPT} ...")
    processor = LayoutLMv3Processor.from_pretrained(CKPT, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(CKPT).to("cuda").eval()
    id2label = model.config.id2label
    pred_total_class = find_class_idx(id2label, "Total_value")
    pred_price_class = find_class_idx(id2label, "Prod_price_value")
    print(f"Model output classes: Total_value={pred_total_class}  Prod_price_value={pred_price_class}")
    if pred_total_class is None:
        raise RuntimeError("model has no Total_value class in id2label")

    test_lines = (WILD_DIR / "test.txt").read_text().splitlines()
    receipts = [json.loads(line) for line in test_lines if line.strip()]
    print(f"WildReceipt test n={len(receipts)}")

    results, t0 = [], time.time()
    for i, r in enumerate(receipts):
        anns = r.get("annotations", [])
        img_rel = r.get("file_name")
        if not img_rel:
            continue
        img_path = WILD_DIR / img_rel
        if not img_path.exists():
            continue
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception:
            continue
        w, h = img.size

        words = [a["text"] for a in anns]
        boxes_norm = [normalize_box(quad_to_xyxy(a["box"]), w, h) for a in anns]
        if not words:
            continue

        try:
            encoding = processor(img, words, boxes=boxes_norm,
                                 return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to("cuda") for k, v in encoding.items()}
            with torch.inference_mode():
                out = model(**inputs)
            preds = out.logits.argmax(-1)[0].cpu().tolist()
            word_ids = encoding.word_ids(0)
        except Exception as e:
            if i < 3: print(f"  infer fail {i}: {e}")
            continue

        # First-subtoken vote for word-level prediction.
        word_pred = {}
        for tok_idx, wid in enumerate(word_ids):
            if wid is None: continue
            if wid not in word_pred:
                word_pred[wid] = preds[tok_idx]

        pred_total_words = [words[wid] for wid, pid in word_pred.items()
                            if pid == pred_total_class and wid < len(words)]
        pred_total = parse_money("".join(pred_total_words)) if pred_total_words else None

        gold_total_anns = [parse_money(a["text"]) for a in anns if a.get("label") == TOT_ID]
        gold_total = gold_total_anns[0] if (gold_total_anns and gold_total_anns[0] is not None) else None

        prices_ann = [a for a in anns if a.get("label") == PRC_ID]
        rows = row_group(prices_ann)
        per_line_prices = []
        for row in rows:
            vs = [parse_money(b["text"]) for b in row]
            vs = [v for v in vs if v is not None]
            if vs: per_line_prices.append(sum(vs))
        per_line_prices = per_line_prices[:MAX_MONEY_LINES]
        taxes = [parse_money(a["text"]) for a in anns if a.get("label") == TAX_ID]
        tau = (taxes[0] if taxes and taxes[0] is not None else 0.0) or 0.0

        T = I3_reachable(per_line_prices, tau) if per_line_prices else set()
        in_T = pred_total is not None and any(abs(pred_total - t) <= 0.02 for t in T)
        correct = (pred_total is not None and gold_total is not None
                   and abs(pred_total - gold_total) <= 0.02)

        if i == 0:
            print(f"  [sanity] pred={pred_total} gold={gold_total} "
                  f"|items|={len(per_line_prices)} |T|={len(T)} tau={tau:.2f} in_T={in_T}")

        results.append({"id": i, "pred": pred_total, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T),
                        "items_count": len(per_line_prices), "tau": tau})
        if (i + 1) % 50 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {i+1}/{len(receipts)}  elapsed={time.time()-t0:.0f}s")

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    summary = {
        "checkpoint": CKPT,
        "corpus": "WildReceipt",
        "setup": "in-distribution",
        "n": len(results),
        "wall_sec": round(time.time() - t0, 1),
        "coverage_1.0_F1": correct_all / n,
        "coverage_sigma": len(accepted) / n,
        "sigma_F1_on_accepted": correct_accepted / max(1, len(accepted)),
        "sigma_recall_on_correct": (sum(1 for r in results if r["correct"] and r["in_T"])
                                    / max(1, correct_all)),
        "sigma_precision": correct_accepted / max(1, len(accepted)),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
