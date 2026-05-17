"""MF2: WildReceipt softmax baseline + sigma orthogonality + Pareto.

v2: adds per-receipt results array and softmax_threshold_sweep so that
S_pareto/paper_table can fold WildReceipt into the Pareto frontier
alongside CORD and SROIE. Also outputs a self-contained pareto_front
for WildReceipt directly into the MF2 JSON.

Mirrors F's data loading and LayoutLMv3 inference path but adds softmax
confidence per receipt (geometric mean of per-token max-class softmax
probabilities for tokens predicted as Total_value -- the closest
analogue to DONUT's c_seq on a token-classification backbone).

Outputs:
  - runs/MF2_wildreceipt_softmax.json  (numbers + per-receipt results)
  - paper/asyu/numbers_pooled.tex      (LaTeX renewcommand overrides)

GPU. ~30 s on RTX 4090 + image download if needed.
"""
import gc, json, math, re, tarfile, time, urllib.request
from pathlib import Path

import torch
from PIL import Image
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification

ROOT = Path(__file__).resolve().parents[2]
CKPT = "Theivaprakasham/layoutlmv3-finetuned-wildreceipt"
WILD_URL = "https://download.openmmlab.com/mmocr/data/wildreceipt.tar"
WILD_DIR = ROOT / "data/wildreceipt"
F_OUT = ROOT / "runs/F_layoutlmv3_on_wildreceipt.json"
OUT_JSON = ROOT / "runs/MF2_wildreceipt_softmax.json"
OUT_TEX = ROOT / "paper/asyu/numbers_pooled.tex"
BATCH = 16

LOCKED = {
    # Leakage-free CORD = CORD-v2 test+validation (n=200). CORD-v2 *train*
    # (the Donut fine-tuning split) is excluded. Values from the restored
    # leakage-free runs/MB_cord_baseline.json (commit 073cabc).
    "CORD": {
        "n": 200,
        "sigma_acc": 99,  "sigma_corr": 98,
        "smax_acc":  99,  "smax_corr":  95,
        "int_acc":   55,  "int_corr":   54,
        "sigonly_acc": 44, "sigonly_corr": 44,
        "smonly_acc":  44, "smonly_corr": 41,
        "b_mcnemar": 44, "c_mcnemar": 41,
    },
    "SROIE": {
        "n": 347,
        "sigma_acc": 75,  "sigma_corr": 65,
        "smax_acc":  75,  "smax_corr":  71,
        "int_acc":   15,  "int_corr":   15,
        "sigonly_acc": 60, "sigonly_corr": 50,
        "smonly_acc":  60, "smonly_corr": 56,
        "b_mcnemar": 50, "c_mcnemar": 56,
    },
}


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", ".").replace("$", "").replace("RM", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def ensure_wildreceipt():
    if WILD_DIR.exists() and (WILD_DIR / "test.txt").exists():
        return
    print("Downloading WildReceipt (~70 MB)...")
    (ROOT / "data").mkdir(exist_ok=True)
    tar_path = ROOT / "wildreceipt.tar"
    urllib.request.urlretrieve(WILD_URL, tar_path)
    with tarfile.open(tar_path) as t:
        t.extractall(ROOT / "data")
    tar_path.unlink()


def load_class_list(path):
    cls = {}
    for line in open(path):
        parts = line.strip().split()
        if len(parts) >= 2:
            cls[parts[1]] = int(parts[0])
    return cls


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


def find_class_idx(id2label, target_substring):
    for idx, name in id2label.items():
        if target_substring in name:
            return idx
    return None


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    inner = p * (1 - p) / n + z2 / (4 * n * n)
    margin = (z / (1 + z2 / n)) * (inner ** 0.5)
    return (max(0.0, center - margin), min(1.0, center + margin))


def pareto_front(points):
    """Maximise both coverage and precision. Returns list of
    {coverage, precision, label} in coverage-ascending order."""
    pts = sorted(points, key=lambda p: (-p[1], -p[0]))
    front = []
    max_cov = -1.0
    for cov, prec, lbl in pts:
        if cov > max_cov + 1e-9:
            front.append({"coverage": cov, "precision": prec, "label": lbl})
            max_cov = cov
    return sorted(front, key=lambda x: x["coverage"])


def build_wildreceipt_pareto(f_results, softmax_conf, sigma_accepts):
    """Build Pareto points for WildReceipt across signals:
    sigma alone, softmax sweep, sigma AND softmax_topk, sigma OR softmax_topk.
    """
    n = len(f_results)
    correct_by_id = {rid: r["correct"] for rid, r in f_results.items()}
    sorted_by_conf = sorted(softmax_conf.items(), key=lambda kv: -kv[1])

    points = []
    # sigma alone
    sigma_corr = sum(1 for rid in sigma_accepts if correct_by_id.get(rid, False))
    points.append((len(sigma_accepts) / n, sigma_corr / max(1, len(sigma_accepts)), "sigma"))

    # softmax sweep at various coverage fractions
    for frac in (0.05, 0.10, 0.20, 0.30, 0.45, 0.50, 0.70, 1.0):
        k = int(round(frac * n))
        if k == 0: continue
        topk_ids = {rid for rid, _ in sorted_by_conf[:k]}
        corr = sum(1 for rid in topk_ids if correct_by_id.get(rid, False))
        cov = len(topk_ids) / n
        prec = corr / max(1, len(topk_ids))
        points.append((cov, prec, f"softmax_k={k}"))

    # sigma AND softmax_topk
    for frac in (0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.0):
        k = int(round(frac * n))
        if k == 0: continue
        topk_ids = {rid for rid, _ in sorted_by_conf[:k]}
        joint = sigma_accepts & topk_ids
        if not joint: continue
        corr = sum(1 for rid in joint if correct_by_id.get(rid, False))
        cov = len(joint) / n
        prec = corr / max(1, len(joint))
        points.append((cov, prec, f"sigma_AND_softmax_k={k}"))

    # sigma OR softmax_topk
    for frac in (0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 1.0):
        k = int(round(frac * n))
        if k == 0: continue
        topk_ids = {rid for rid, _ in sorted_by_conf[:k]}
        joint = sigma_accepts | topk_ids
        if not joint: continue
        corr = sum(1 for rid in joint if correct_by_id.get(rid, False))
        cov = len(joint) / n
        prec = corr / max(1, len(joint))
        points.append((cov, prec, f"sigma_OR_softmax_k={k}"))

    return pareto_front(points)


def main():
    ensure_wildreceipt()

    if not F_OUT.exists():
        raise SystemExit(f"Missing {F_OUT}; run F_layoutlmv3_on_wildreceipt.py first.")
    f_data = json.loads(F_OUT.read_text())
    f_results = {r["id"]: r for r in f_data["results"]}

    cls = load_class_list(WILD_DIR / "class_list.txt")
    print(f"Loading {CKPT}...")
    processor = LayoutLMv3Processor.from_pretrained(CKPT, apply_ocr=False)
    model = LayoutLMv3ForTokenClassification.from_pretrained(CKPT).to("cuda").eval()
    id2label = model.config.id2label
    pred_total_class = find_class_idx(id2label, "Total_value")

    test_lines = (WILD_DIR / "test.txt").read_text().splitlines()
    receipts = [json.loads(line) for line in test_lines if line.strip()]
    print(f"WildReceipt test n={len(receipts)}")

    items = []
    for i, r in enumerate(receipts):
        anns = r.get("annotations", [])
        img_rel = r.get("file_name")
        if not img_rel: continue
        img_path = WILD_DIR / img_rel
        if not img_path.exists(): continue
        try: img = Image.open(img_path).convert("RGB")
        except Exception: continue
        w, h = img.size
        words = [a["text"] for a in anns]
        boxes = [normalize_box(quad_to_xyxy(a["box"]), w, h) for a in anns]
        if not words: continue
        items.append({"i": i, "img": img, "words": words, "boxes": boxes})

    print(f"LayoutLMv3 with softmax (batch={BATCH}) on {len(items)}...")
    t0 = time.time()
    per_receipt_softmax = {}
    for j in range(0, len(items), BATCH):
        batch = items[j:j + BATCH]
        encoding = processor(
            [b["img"] for b in batch],
            text=[b["words"] for b in batch],
            boxes=[b["boxes"] for b in batch],
            return_tensors="pt", padding=True, truncation=True, max_length=512,
        )
        inputs = {k: v.to("cuda") for k, v in encoding.items()}
        with torch.inference_mode():
            out = model(**inputs)
        probs = torch.softmax(out.logits, dim=-1)
        preds = out.logits.argmax(-1).cpu().tolist()

        for b_idx, item in enumerate(batch):
            word_ids = encoding.word_ids(batch_index=b_idx)
            total_token_probs = []
            for tok_idx, wid in enumerate(word_ids):
                if wid is None: continue
                if preds[b_idx][tok_idx] == pred_total_class:
                    p = probs[b_idx, tok_idx, pred_total_class].item()
                    total_token_probs.append(p)
            if total_token_probs:
                log_p = sum(math.log(max(p, 1e-12)) for p in total_token_probs) / len(total_token_probs)
                per_receipt_softmax[item["i"]] = math.exp(log_p)
            else:
                per_receipt_softmax[item["i"]] = 0.0

        if (j // BATCH + 1) % 5 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {min(j + BATCH, len(items))}/{len(items)} elapsed={time.time() - t0:.0f}s")
    print(f"LayoutLMv3+softmax done in {time.time() - t0:.1f}s")

    n_total = len(f_results)
    sigma_accepts = {rid for rid, r in f_results.items() if r["in_T"]}
    n_sigma = len(sigma_accepts)
    sorted_by_conf = sorted(per_receipt_softmax.items(), key=lambda x: -x[1])
    softmax_accepts = {rid for rid, _ in sorted_by_conf[:n_sigma]}

    int_accepts = sigma_accepts & softmax_accepts
    sig_only = sigma_accepts - softmax_accepts
    smax_only = softmax_accepts - sigma_accepts

    def corr_count(ids):
        return sum(1 for rid in ids if f_results.get(rid, {}).get("correct"))

    wr = {
        "n": n_total,
        "sigma_acc": n_sigma, "sigma_corr": corr_count(sigma_accepts),
        "smax_acc":  len(softmax_accepts), "smax_corr":  corr_count(softmax_accepts),
        "int_acc":   len(int_accepts),     "int_corr":   corr_count(int_accepts),
        "sigonly_acc": len(sig_only),      "sigonly_corr": corr_count(sig_only),
        "smonly_acc":  len(smax_only),     "smonly_corr": corr_count(smax_only),
    }

    sigma_correct_ids = {rid for rid in sigma_accepts if f_results[rid]["correct"]}
    smax_correct_ids = {rid for rid in softmax_accepts if f_results[rid]["correct"]}
    wr["b_mcnemar"] = len(sigma_correct_ids - smax_correct_ids)
    wr["c_mcnemar"] = len(smax_correct_ids - sigma_correct_ids)

    # v2: per-receipt results array (for S_pareto/paper_table downstream)
    results_array = []
    for rid, r in f_results.items():
        results_array.append({
            "id": rid,
            "sigma_accept": r.get("in_T", False),
            "softmax_score": per_receipt_softmax.get(rid),
            "correct": r.get("correct", False),
        })

    # v2: WildReceipt Pareto frontier
    pareto = build_wildreceipt_pareto(f_results, per_receipt_softmax, sigma_accepts)

    # Pooled
    def pool(key):
        return LOCKED["CORD"][key] + LOCKED["SROIE"][key] + wr[key]
    pooled = {k: pool(k) for k in (
        "n", "sigma_acc", "sigma_corr", "smax_acc", "smax_corr",
        "int_acc", "int_corr", "sigonly_acc", "sigonly_corr",
        "smonly_acc", "smonly_corr", "b_mcnemar", "c_mcnemar",
    )}

    def wci(k, n):
        lo, hi = wilson_ci(k, n)
        return (round(lo, 3), round(hi, 3))
    pooled_ci = {
        "sigma":   wci(pooled["sigma_corr"],   pooled["sigma_acc"]),
        "smax":    wci(pooled["smax_corr"],    pooled["smax_acc"]),
        "int":     wci(pooled["int_corr"],     pooled["int_acc"]),
        "sigonly": wci(pooled["sigonly_corr"], pooled["sigonly_acc"]),
        "smonly":  wci(pooled["smonly_corr"],  pooled["smonly_acc"]),
    }

    bp, cp = pooled["b_mcnemar"], pooled["c_mcnemar"]
    chi2_pooled = ((abs(bp - cp) - 1) ** 2) / max(1, bp + cp)
    try:
        from scipy.stats import chi2 as chi2_dist
        p_pooled = float(chi2_dist.sf(chi2_pooled, 1))
    except Exception:
        p_pooled = math.erfc((chi2_pooled / 2) ** 0.5)

    result = {
        "WildReceipt": wr,
        "WildReceipt_pareto_front": pareto,
        "WildReceipt_results": results_array,
        "Pooled": pooled,
        "Pooled_CIs": pooled_ci,
        "Pooled_McNemar": {"b": bp, "c": cp,
                            "chi2": round(chi2_pooled, 4),
                            "p_value": round(p_pooled, 4)},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "WildReceipt_results"}, indent=2))

    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    tex_lines = [
        "% Auto-generated by scripts/smoke/MF2_wildreceipt_softmax.py",
        f"\\renewcommand{{\\poolN}}{{{pooled['n']}}}",
        f"\\renewcommand{{\\poolSigA}}{{{pooled['sigma_acc']}}}",
        f"\\renewcommand{{\\poolSigC}}{{{pooled['sigma_corr']}}}",
        f"\\renewcommand{{\\poolIntA}}{{{pooled['int_acc']}}}",
        f"\\renewcommand{{\\poolIntC}}{{{pooled['int_corr']}}}",
        f"\\renewcommand{{\\poolMcB}}{{{bp}}}",
        f"\\renewcommand{{\\poolMcC}}{{{cp}}}",
        f"\\renewcommand{{\\poolMcChi}}{{{chi2_pooled:.3f}}}",
        f"\\renewcommand{{\\poolMcP}}{{{p_pooled:.3f}}}",
        f"\\renewcommand{{\\wrN}}{{{wr['n']}}}",
        f"\\renewcommand{{\\wrIntA}}{{{wr['int_acc']}}}",
        f"\\renewcommand{{\\wrIntC}}{{{wr['int_corr']}}}",
        "",
    ]
    OUT_TEX.write_text("\n".join(tex_lines))
    print(f"\nWrote {OUT_TEX}")


if __name__ == "__main__":
    main()
