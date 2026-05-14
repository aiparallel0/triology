"""MF2: WildReceipt softmax baseline + sigma orthogonality.

Mirrors F's data loading and LayoutLMv3 inference path but adds softmax
confidence per receipt. The softmax signal is the geometric mean of
per-token max-class softmax probabilities for tokens that the model
predicts as Total_value -- the closest analogue to DONUT's c_seq on a
token-classification backbone.

Reads runs/F_layoutlmv3_on_wildreceipt.json for sigma verdicts per
receipt (sigma accept/reject + correctness). Matches coverage to the
sigma accept count (n=214 of 472) by ranking softmax confidences and
taking the top-n. Computes the four-cell orthogonality matrix on
WildReceipt and combines with the locked CORD+SROIE numbers to write a
pooled benchmark with n=919.

Outputs:
  - runs/MF2_wildreceipt_softmax.json  (full numbers)
  - paper/asyu/numbers_pooled.tex      (LaTeX renewcommand overrides)

GPU. ~30 s on RTX 4090 (inference) + image download if needed.
"""
import gc, json, re, tarfile, time, urllib.request
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


# Locked CORD + SROIE numbers (from runs/M_baseline_softmax.json,
# MB_cord_baseline.json, T_significance.json). Direct copies, not
# recomputations.
LOCKED = {
    "CORD": {
        "n": 100,
        "sigma_acc": 55,  "sigma_corr": 54,
        "smax_acc":  55,  "smax_corr":  51,
        "int_acc":   33,  "int_corr":   32,
        "sigonly_acc": 22, "sigonly_corr": 22,
        "smonly_acc":  22, "smonly_corr": 19,
        "b_mcnemar": 22, "c_mcnemar": 19,
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

    # Pre-load images + per-receipt aux data
    items = []
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
        boxes = [normalize_box(quad_to_xyxy(a["box"]), w, h) for a in anns]
        if not words:
            continue
        items.append({"i": i, "img": img, "words": words, "boxes": boxes})

    print(f"LayoutLMv3 with softmax (batch={BATCH}) on {len(items)}...")
    t0 = time.time()
    per_receipt_softmax = {}  # id -> geometric_mean_prob_for_total_value_tokens
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
        # out.logits: (batch, seq_len, num_classes)
        probs = torch.softmax(out.logits, dim=-1)
        preds = out.logits.argmax(-1).cpu().tolist()

        for b_idx, item in enumerate(batch):
            word_ids = encoding.word_ids(batch_index=b_idx)
            total_token_probs = []
            for tok_idx, wid in enumerate(word_ids):
                if wid is None:
                    continue
                if preds[b_idx][tok_idx] == pred_total_class:
                    # Token classified as Total_value: take its softmax prob
                    p = probs[b_idx, tok_idx, pred_total_class].item()
                    total_token_probs.append(p)
            if total_token_probs:
                # Geometric mean of per-token probabilities -- analogue of c_seq
                import math
                log_p = sum(math.log(max(p, 1e-12)) for p in total_token_probs) / len(total_token_probs)
                per_receipt_softmax[item["i"]] = math.exp(log_p)
            else:
                # No total predicted -> 0 confidence
                per_receipt_softmax[item["i"]] = 0.0

        if (j // BATCH + 1) % 5 == 0:
            gc.collect()
            torch.cuda.empty_cache()
            print(f"  {min(j + BATCH, len(items))}/{len(items)} elapsed={time.time() - t0:.0f}s")
    print(f"LayoutLMv3+softmax done in {time.time() - t0:.1f}s")

    # Match coverage to sigma: rank by softmax conf descending, take top-n_sigma_accept
    n_total = len(f_results)
    sigma_accepts = {rid for rid, r in f_results.items() if r["in_T"]}
    n_sigma = len(sigma_accepts)
    sorted_by_conf = sorted(
        per_receipt_softmax.items(), key=lambda x: -x[1]
    )
    softmax_accepts = {rid for rid, _ in sorted_by_conf[:n_sigma]}

    int_accepts = sigma_accepts & softmax_accepts
    sig_only = sigma_accepts - softmax_accepts
    smax_only = softmax_accepts - sigma_accepts

    def corr_count(ids):
        return sum(1 for rid in ids if f_results.get(rid, {}).get("correct"))

    wr_sigma_acc = n_sigma
    wr_sigma_corr = corr_count(sigma_accepts)
    wr_smax_acc = len(softmax_accepts)
    wr_smax_corr = corr_count(softmax_accepts)
    wr_int_acc = len(int_accepts)
    wr_int_corr = corr_count(int_accepts)
    wr_sigonly_acc = len(sig_only)
    wr_sigonly_corr = corr_count(sig_only)
    wr_smonly_acc = len(smax_only)
    wr_smonly_corr = corr_count(smax_only)

    # McNemar discordant cells for WildReceipt
    # b = sigma correct AND softmax accept-or-correct-fail combinations
    # Following the existing T_significance convention:
    # b = sigma correct AND not (softmax-correct), c = softmax correct AND not (sigma-correct)
    sigma_correct_ids = {rid for rid in sigma_accepts if f_results[rid]["correct"]}
    smax_correct_ids = {rid for rid in softmax_accepts if f_results[rid]["correct"]}
    b_wr = len(sigma_correct_ids - smax_correct_ids)
    c_wr = len(smax_correct_ids - sigma_correct_ids)

    wr = {
        "n": n_total,
        "sigma_acc": wr_sigma_acc, "sigma_corr": wr_sigma_corr,
        "smax_acc":  wr_smax_acc,  "smax_corr":  wr_smax_corr,
        "int_acc":   wr_int_acc,   "int_corr":   wr_int_corr,
        "sigonly_acc": wr_sigonly_acc, "sigonly_corr": wr_sigonly_corr,
        "smonly_acc":  wr_smonly_acc,  "smonly_corr": wr_smonly_corr,
        "b_mcnemar": b_wr, "c_mcnemar": c_wr,
    }

    # Pooled: CORD + SROIE + WildReceipt
    def pool(key):
        return LOCKED["CORD"][key] + LOCKED["SROIE"][key] + wr[key]

    pooled = {
        "n":           pool("n"),
        "sigma_acc":   pool("sigma_acc"),
        "sigma_corr":  pool("sigma_corr"),
        "smax_acc":    pool("smax_acc"),
        "smax_corr":   pool("smax_corr"),
        "int_acc":     pool("int_acc"),
        "int_corr":    pool("int_corr"),
        "sigonly_acc": pool("sigonly_acc"),
        "sigonly_corr": pool("sigonly_corr"),
        "smonly_acc":  pool("smonly_acc"),
        "smonly_corr": pool("smonly_corr"),
        "b_mcnemar":   pool("b_mcnemar"),
        "c_mcnemar":   pool("c_mcnemar"),
    }

    # Wilson CIs for pooled cells
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

    # Pooled McNemar
    bp, cp = pooled["b_mcnemar"], pooled["c_mcnemar"]
    chi2_pooled = ((abs(bp - cp) - 1) ** 2) / max(1, bp + cp)
    # p-value: chi^2 with 1 df is the survival function; approximate via
    # scipy if available, else math.erfc
    try:
        from scipy.stats import chi2 as chi2_dist
        p_pooled = float(chi2_dist.sf(chi2_pooled, 1))
    except Exception:
        import math
        p_pooled = math.erfc((chi2_pooled / 2) ** 0.5)

    result = {
        "WildReceipt": wr,
        "Pooled": pooled,
        "Pooled_CIs": pooled_ci,
        "Pooled_McNemar": {"b": bp, "c": cp,
                            "chi2": round(chi2_pooled, 4),
                            "p_value": round(p_pooled, 4)},
    }
    OUT_JSON.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

    # Write paper LaTeX overrides
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    tex_lines = [
        "% Auto-generated by scripts/smoke/MF2_wildreceipt_softmax.py",
        "% Three-corpus pooled benchmark (CORD + SROIE + WildReceipt).",
        f"\\renewcommand{{\\poolN}}{{{pooled['n']}}}",
        f"\\renewcommand{{\\poolSigA}}{{{pooled['sigma_acc']}}}",
        f"\\renewcommand{{\\poolSigC}}{{{pooled['sigma_corr']}}}",
        f"\\renewcommand{{\\poolSigP}}{{{pooled['sigma_corr']/pooled['sigma_acc']:.3f}}}",
        f"\\renewcommand{{\\poolSigCI}}{{[{pooled_ci['sigma'][0]:.3f}, {pooled_ci['sigma'][1]:.3f}]}}",
        f"\\renewcommand{{\\poolSmA}}{{{pooled['smax_acc']}}}",
        f"\\renewcommand{{\\poolSmC}}{{{pooled['smax_corr']}}}",
        f"\\renewcommand{{\\poolSmP}}{{{pooled['smax_corr']/pooled['smax_acc']:.3f}}}",
        f"\\renewcommand{{\\poolSmCI}}{{[{pooled_ci['smax'][0]:.3f}, {pooled_ci['smax'][1]:.3f}]}}",
        f"\\renewcommand{{\\poolIntA}}{{{pooled['int_acc']}}}",
        f"\\renewcommand{{\\poolIntC}}{{{pooled['int_corr']}}}",
        f"\\renewcommand{{\\poolIntP}}{{{pooled['int_corr']/pooled['int_acc']:.3f}}}",
        f"\\renewcommand{{\\poolIntCI}}{{[{pooled_ci['int'][0]:.3f}, {pooled_ci['int'][1]:.3f}]}}",
        f"\\renewcommand{{\\poolSigOnlyA}}{{{pooled['sigonly_acc']}}}",
        f"\\renewcommand{{\\poolSigOnlyC}}{{{pooled['sigonly_corr']}}}",
        f"\\renewcommand{{\\poolSigOnlyP}}{{{pooled['sigonly_corr']/pooled['sigonly_acc']:.3f}}}",
        f"\\renewcommand{{\\poolSigOnlyCI}}{{[{pooled_ci['sigonly'][0]:.3f}, {pooled_ci['sigonly'][1]:.3f}]}}",
        f"\\renewcommand{{\\poolSmOnlyA}}{{{pooled['smonly_acc']}}}",
        f"\\renewcommand{{\\poolSmOnlyC}}{{{pooled['smonly_corr']}}}",
        f"\\renewcommand{{\\poolSmOnlyP}}{{{pooled['smonly_corr']/pooled['smonly_acc']:.3f}}}",
        f"\\renewcommand{{\\poolSmOnlyCI}}{{[{pooled_ci['smonly'][0]:.3f}, {pooled_ci['smonly'][1]:.3f}]}}",
        f"\\renewcommand{{\\poolMcB}}{{{bp}}}",
        f"\\renewcommand{{\\poolMcC}}{{{cp}}}",
        f"\\renewcommand{{\\poolMcChi}}{{{chi2_pooled:.3f}}}",
        f"\\renewcommand{{\\poolMcP}}{{{p_pooled:.3f}}}",
        # WildReceipt-only row for the per-corpus stability table:
        f"\\renewcommand{{\\wrN}}{{{wr['n']}}}",
        f"\\renewcommand{{\\wrIntA}}{{{wr['int_acc']}}}",
        f"\\renewcommand{{\\wrIntC}}{{{wr['int_corr']}}}",
        f"\\renewcommand{{\\wrIntCI}}{{[{wilson_ci(wr['int_corr'], wr['int_acc'])[0]:.3f}, {wilson_ci(wr['int_corr'], wr['int_acc'])[1]:.3f}]}}",
        "",
    ]
    OUT_TEX.write_text("\n".join(tex_lines))
    print(f"\nWrote {OUT_TEX}")
    print("Recompile paper/asyu/main.tex to pick up n=919 pooled numbers.")


if __name__ == "__main__":
    main()
