"""time_budget: measure DONUT inference time vs sigma DP time per receipt.

Quotes a hard number for the paper: 'sigma adds X% to inference cost.'

Protocol:
  - Load DONUT-CORD finetuned model
  - Sample 20 CORD test receipts
  - For each: time generate() call (DONUT) + time I3 DP (sigma)
  - Report mean/p95/p99 for both + ratio sigma_DP / DONUT_generate

Runtime ~30 sec on RTX 4090.
"""
import gc, json, os, sys, time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
OUT = Path("runs/time_budget.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
N_RECEIPTS = int(os.environ.get("TIME_BUDGET_N", "20"))
DP_REPEATS = 100  # repeat DP to get stable timing on fast operations


def parse_money(s):
    try: return float(str(s).replace(",", ""))
    except (TypeError, ValueError): return None


def extract_cord(ex):
    gt = ex.get("ground_truth")
    if isinstance(gt, str):
        try: gt = json.loads(gt)
        except Exception: return None, None, None
    if not isinstance(gt, dict): return None, None, None
    gt = gt.get("gt_parse", gt) if "gt_parse" in gt else gt
    menu = gt.get("menu") or []
    if isinstance(menu, dict): menu = [menu]
    items = []
    for m in menu:
        if isinstance(m, dict):
            p = parse_money(m.get("price"))
            if p is not None: items.append(p)
    total_info = gt.get("total") or {}
    total = parse_money(total_info.get("total_price")) if isinstance(total_info, dict) else None
    tax = parse_money(total_info.get("tax_price")) if isinstance(total_info, dict) else 0.0
    return items, total, (tax if tax is not None else 0.0)


def i3_reachable(money, tau, eps=0.02):
    if not money: return set()
    kmin = 1 if abs(tau) > eps else 2
    cents = [int(round(v * 100)) for v in money]
    tau_c = int(round(tau * 100))
    D = {0: 0}
    for v in cents:
        new = dict(D)
        for s, k in D.items():
            ns = s + v
            if ns not in new or new[ns] > k + 1: new[ns] = k + 1
        D = new
    return {(s + tau_c) / 100.0 for s, k in D.items() if k >= kmin}


def main():
    t0 = time.time()
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()
    dec_one = processor.tokenizer("<s_cord-v2>", add_special_tokens=False, return_tensors="pt").input_ids
    pad_id = processor.tokenizer.pad_token_id

    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    sample = list(range(min(N_RECEIPTS, len(ds))))

    # Warm up
    img = ds[0]["image"].convert("RGB")
    px = processor([img], return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
    dec = dec_one.to("cuda")
    with torch.inference_mode():
        _ = model.generate(px, decoder_input_ids=dec, max_length=512, num_beams=1, pad_token_id=pad_id)

    donut_times_ms = []
    dp_times_ms = []

    for ex_idx in sample:
        ex = ds[ex_idx]
        try: img = ex["image"].convert("RGB")
        except Exception: continue

        px = processor([img], return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        dec = dec_one.to("cuda")

        # Time DONUT inference
        torch.cuda.synchronize()
        t_start = time.perf_counter()
        with torch.inference_mode():
            _ = model.generate(px, decoder_input_ids=dec, max_length=512, num_beams=1, pad_token_id=pad_id)
        torch.cuda.synchronize()
        donut_ms = (time.perf_counter() - t_start) * 1000
        donut_times_ms.append(donut_ms)

        # Time DP (repeat for stable measurement)
        items, total, tau = extract_cord(ex)
        if not items: continue
        t_dp = time.perf_counter()
        for _ in range(DP_REPEATS):
            T = i3_reachable(items, tau)
        dp_ms = ((time.perf_counter() - t_dp) / DP_REPEATS) * 1000
        dp_times_ms.append(dp_ms)

    def stats(xs):
        if not xs: return None
        xs_sorted = sorted(xs)
        n = len(xs_sorted)
        return {
            "n": n,
            "mean": sum(xs_sorted) / n,
            "median": xs_sorted[n // 2],
            "p95": xs_sorted[int(0.95 * n)] if n >= 20 else xs_sorted[-1],
            "p99": xs_sorted[int(0.99 * n)] if n >= 100 else xs_sorted[-1],
            "min": xs_sorted[0],
            "max": xs_sorted[-1],
        }

    donut_stats = stats(donut_times_ms)
    dp_stats = stats(dp_times_ms)

    ratio = None
    pct = None
    if donut_stats and dp_stats and donut_stats["mean"] > 0:
        ratio = dp_stats["mean"] / donut_stats["mean"]
        pct = 100 * ratio

    summary = {
        "ckpt": CKPT,
        "n_receipts": N_RECEIPTS,
        "dp_repeats_per_receipt": DP_REPEATS,
        "wall_sec": round(time.time() - t0, 1),
        "donut_generate_ms": donut_stats,
        "sigma_dp_ms": dp_stats,
        "sigma_overhead_ratio": ratio,
        "sigma_overhead_percent": pct,
        "interpretation": (
            "sigma_overhead_percent is the fraction of total inference time added by sigma. "
            "Typical expectation: DONUT generate takes ~50-150ms; sigma DP takes ~0.005-1ms. "
            "Ratio should be < 1% on a single GPU, supporting the 'sigma is essentially free at "
            "deployment' claim."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
