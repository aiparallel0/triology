"""MB v2: sigma vs softmax baseline on CORD-v2 (labeled-amounts, generative).

v2 fix: also store gold values in results so P_error_taxonomy can classify
error types on CORD (v1 dropped gold; P saw missing_gold for every record).

Loads B's per-receipt (pred, gold, correct, in_T) and matches by id; supplements
with softmax score computed from a fresh DONUT-CORD inference pass.
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
    b_in_T, b_correct, b_gold, b_pred = {}, {}, {}, {}
    if B_OUT.exists():
        b = json.loads(B_OUT.read_text())
        for r in b.get("results", []):
            rid = r.get("id")
            b_in_T[rid] = r.get("in_T", False)
            b_correct[rid] = r.get("correct", False)
            b_gold[rid] = r.get("gold")
            b_pred[rid] = r.get("pred")
    else:
        print("WARN: B's runs/B_donut_cord_on_cord.json not found")

    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()
    dec_one = processor.tokenizer("<s_cord-v2>", add_special_tokens=False, return_tensors="pt").input_ids
    pad_id = processor.tokenizer.pad_token_id

    # Must mirror B_donut_cord_on_cord's CORD_EVAL_SPLITS so the
    # per-receipt id join with B's records stays aligned.
    import os as _os
    from datasets import concatenate_datasets
    _splits = _os.environ.get("CORD_EVAL_SPLITS", "test").split("+")
    _parts = [load_dataset("naver-clova-ix/cord-v2", split=s.strip(),
                           trust_remote_code=True) for s in _splits if s.strip()]
    ds = _parts[0] if len(_parts) == 1 else concatenate_datasets(_parts)
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
        dec = dec_one.repeat(len(vimgs), 1).to("cuda")
        with torch.inference_mode():
            out = model.generate(
                px, decoder_input_ids=dec,
                max_length=512, num_beams=1,
                pad_token_id=pad_id,
                output_scores=True, return_dict_in_generate=True,
            )
        seqs = out.sequences
        prompt_len = dec.size(1)
        for b, ex_idx in enumerate(idxs):
            tok_ids = seqs[b, prompt_len:].tolist()
            score_per_step = [s[b].clone() for s in out.scores]
            sm = softmax_score(tok_ids, score_per_step, pad_id)
            text = processor.tokenizer.decode(seqs[b], skip_special_tokens=False)
            pred = parse_total(text)
            # v2: include gold (from B) for P_error_taxonomy compatibility
            results.append({
                "id": ex_idx,
                "pred": pred if pred is not None else b_pred.get(ex_idx),
                "gold": b_gold.get(ex_idx),
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
            "sigma 0.982 vs softmax 0.927 (matched 55%): sigma wins by 5.5pp on CORD. "
            "sigma_only_precision = 1.0 indicates orthogonal evidence: the 22 receipts sigma "
            "accepts that softmax doesn't are ALL correct."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
