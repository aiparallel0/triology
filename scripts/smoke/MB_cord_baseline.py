"""MB: sigma vs softmax baseline on CORD-v2 (labeled-amounts regime, generative).

Tests whether softmax-thresholding dominates sigma on CORD where B reports
sigma_precision=0.98 @ 55% coverage. If softmax ALSO reaches that operating
point, the regime distinction claim (sigma wins on labeled corpora, softmax
wins on OCR-derived) collapses and Paper 1's headline weakens.

Protocol mirrors M (SROIE): re-runs DONUT-CORD with output_scores=True,
computes geo-mean softmax over the predicted sequence, compares to sigma's
accept set from B's prior run at matched coverage.

Runtime ~60s on RTX 4090.
"""
import gc, json, os, re, sys, time
from pathlib import Path

import numpy as np
import torch
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
B_OUT = Path("runs/B_donut_cord_on_cord.json")
OUT = Path("runs/MB_cord_baseline.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
BATCH = int(os.environ.get("DONUT_BATCH", "8"))


def parse_money(s):
    if s is None: return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None


def parse_total(text):
    m = re.search(r"<s_total_price>([^<]+)", text)
    if m is None:
        m = re.search(r"<s_total>([^<]+)", text)
    return parse_money(m.group(1)) if m else None


def softmax_score(tok_ids, scores, pad_id):
    if not scores or not tok_ids: return None
    log_ps = []
    for step, score in enumerate(scores):
        if step >= len(tok_ids): break
        tok = tok_ids[step]
        if tok == pad_id: break
        probs = torch.softmax(score.float(), dim=-1)
        p = probs[tok].clamp_min(1e-12).item()
        log_ps.append(float(np.log(p)))
    return float(np.exp(np.mean(log_ps))) if log_ps else None


def main():
    t0 = time.time()
    # Load B's results
    b_in_T, b_correct = {}, {}
    if B_OUT.exists():
        b = json.loads(B_OUT.read_text())
        for r in b.get("results", []):
            rid = r.get("id")
            b_in_T[rid] = r.get("in_T", False)
            b_correct[rid] = r.get("correct", False)
    else:
        print("WARN: B's runs/B_donut_cord_on_cord.json not found; sigma_accept will be unknown")

    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()
    start_id = model.config.decoder_start_token_id
    pad_id = processor.tokenizer.pad_token_id

    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    print(f"CORD test n={len(ds)}")

    results = []
    t1 = time.time()
    for i in range(0, len(ds), BATCH):
        batch_idx = list(range(i, min(i + BATCH, len(ds))))
        batch = [ds[j] for j in batch_idx]
        imgs = []
        for ex in batch:
            try: imgs.append(ex["image"].convert("RGB"))
            except Exception: imgs.append(None)
        valid = [(idx, im) for idx, im in zip(batch_idx, imgs) if im is not None]
        if not valid: continue
        idxs, vimgs = zip(*valid)
        px = processor(list(vimgs), return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        with torch.inference_mode():
            out = model.generate(
                px, max_length=512, num_beams=1,
                pad_token_id=pad_id,
                decoder_start_token_id=start_id,
                output_scores=True, return_dict_in_generate=True,
            )
        seqs = out.sequences
        for b, ex_idx in enumerate(idxs):
            tok_ids = seqs[b, 1:].tolist()
            score_per_step = [s[b].clone() for s in out.scores]
            sm = softmax_score(tok_ids, score_per_step, pad_id)
            text = processor.tokenizer.decode(seqs[b], skip_special_tokens=False)
            pred = parse_total(text)
            results.append({
                "id": ex_idx, "pred": pred,
                "correct": b_correct.get(ex_idx, False),
                "softmax_score": sm,
                "sigma_accept": b_in_T.get(ex_idx, False),
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
    for frac in (0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.55, 0.70, 0.85, 1.0):
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
        "corpus": "CORD-v2 test (labeled-amounts, generative)",
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
            "If softmax_matched.precision >= sigma.precision, sigma does NOT win on CORD either, "
            "and the labeled-vs-OCR regime distinction collapses. Paper 1's contribution shifts "
            "entirely to orthogonality (intersect_precision) rather than 'sigma beats softmax on "
            "labeled corpora'. Check intersect_precision vs each gate alone."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
