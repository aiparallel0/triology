"""DONUT-CORD on CORD-test → I3 selective prediction (in-distribution) v3.

Reports SELECTIVE PREDICTION metrics, not 'net F1 lift':
  - F1 at coverage 1.0 (no abstention)
  - F1 at coverage = accept_rate (Σ-accepted only)
  - Sigma recall on correct (was the verifier sound for correct preds?)
  - Sigma precision (purity of accepted set)

~45 s on RTX 4090.
"""
import json, os, re, time, urllib.request
from io import BytesIO
from pathlib import Path

import torch
from PIL import Image
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
OUT = Path("runs/B_donut_cord_on_cord.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_donut_total(text):
    for tag in ("<s_total.total_price>", "<s_total_price>", "<s_total>"):
        m = re.search(re.escape(tag) + r"([^<]+)", text)
        if m: return parse_money(m.group(1))
    return None


def cord_money_lines(menu):
    money = []
    if isinstance(menu, dict): menu = [menu]
    for item in menu or []:
        for k in ("price", "unitprice"):
            v = parse_money(item.get(k))
            if v is not None:
                money.append(v); break
    return money


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


def load_img(img_field):
    if hasattr(img_field, "convert"):
        return img_field.convert("RGB")
    if isinstance(img_field, dict):
        if img_field.get("bytes"):
            return Image.open(BytesIO(img_field["bytes"])).convert("RGB")
        if img_field.get("path"):
            return Image.open(img_field["path"]).convert("RGB")
    if isinstance(img_field, str):
        if img_field.startswith(("http://", "https://")):
            with urllib.request.urlopen(img_field) as r:
                return Image.open(BytesIO(r.read())).convert("RGB")
        return Image.open(img_field).convert("RGB")
    if isinstance(img_field, (bytes, bytearray)):
        return Image.open(BytesIO(img_field)).convert("RGB")
    raise ValueError(f"Cannot load image from type={type(img_field).__name__}")


def main():
    import gc
    from concurrent.futures import ThreadPoolExecutor
    BATCH = int(os.environ.get("DONUT_BATCH", "32"))
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    DTYPE = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=DTYPE).to("cuda").eval()
    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    print(f"CORD-v2 test size: {len(ds)}")
    pad_id = processor.tokenizer.pad_token_id
    dec_one = processor.tokenizer("<s_cord-v2>", add_special_tokens=False,
                                  return_tensors="pt").input_ids

    # Parallel image preload, then batched autoregressive decode.
    def _load(idx):
        try: return (idx, load_img(ds[idx]["image"]))
        except Exception: return None
    with ThreadPoolExecutor(max_workers=8) as ex_:
        loaded = [x for x in ex_.map(_load, range(len(ds))) if x is not None]

    t0 = time.time()
    text_by_idx = {}
    i, bs = 0, BATCH
    print(f"Batched DONUT (batch={BATCH}, {DTYPE}) on {len(loaded)} images...")
    while i < len(loaded):
        chunk = loaded[i:i+bs]
        try:
            px = processor([im for _, im in chunk], return_tensors="pt").pixel_values.to("cuda", dtype=DTYPE)
            dec = dec_one.repeat(len(chunk), 1).to("cuda")
            with torch.inference_mode():
                out = model.generate(px, decoder_input_ids=dec, max_length=512,
                                     num_beams=1, use_cache=True, pad_token_id=pad_id)
            for (idx, _), txt in zip(chunk, processor.batch_decode(out, skip_special_tokens=False)):
                text_by_idx[idx] = txt
            i += bs
        except torch.cuda.OutOfMemoryError:
            gc.collect(); torch.cuda.empty_cache()
            if bs > 1:
                bs = max(1, bs // 2); continue
            text_by_idx[chunk[0][0]] = ""; i += 1
        if (i // max(bs, 1)) % 5 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {min(i, len(loaded))}/{len(loaded)} elapsed={time.time()-t0:.0f}s")

    results = []
    for i, ex in enumerate(ds):
        if i not in text_by_idx:
            continue
        text = text_by_idx[i]
        pred = parse_donut_total(text)

        try:
            gt = json.loads(ex["ground_truth"]).get("gt_parse", {})
        except Exception:
            gt = {}
        gold_total = parse_money((gt.get("total") or {}).get("total_price"))
        money = cord_money_lines(gt.get("menu"))
        sub = gt.get("sub_total") or {}
        tau = ((parse_money(sub.get("tax_price")) or 0.0)
               + (parse_money(sub.get("service_price")) or 0.0)
               - (parse_money(sub.get("discount_price")) or 0.0))

        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold_total is not None
                   and abs(pred - gold_total) <= 0.02)

        if i == 0:
            print(f"  [sanity] pred={pred} gold={gold_total} |money|={len(money)} |T|={len(T)} tau={tau:.2f}")

        results.append({"id": i, "pred": pred, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T)})

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    summary = {
        "n": len(results),
        "wall_sec": round(time.time() - t0, 1),
        "coverage_1.0_F1": correct_all / n,
        "coverage_sigma": len(accepted) / n,
        "sigma_F1_on_accepted": correct_accepted / max(1, len(accepted)),
        "sigma_recall_on_correct": (sum(1 for r in results if r["correct"] and r["in_T"])
                                    / max(1, correct_all)),
        "sigma_precision": correct_accepted / max(1, len(accepted)),
        "selective_prediction_note": "sigma is a precision gate, not a net F1 lift.",
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
