"""DONUT-CORD on CORD-test → I3 before/after F1 (in-distribution end-task).

Paper 1 in-distribution end-task validation. ~45 s on RTX 4090.
Success: F1_sigma_strict - F1_bare ≥ +0.03.
"""
import json, os, re, time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
OUT = Path("runs/B_donut_cord_on_cord.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

from A_donut_cord_on_sroie import (  # reuse helpers when run as script in same dir
    parse_money, parse_donut_total, extract_money_lines, I3_reachable,
) if False else (None,)  # noqa

# Inline copies (avoid same-dir import gotchas):
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
    """CORD-v2 stores items under 'menu' with .price per item plus .sub_total.* fields."""
    money, tau = [], 0.0
    if isinstance(menu, dict): menu = [menu]
    for item in menu or []:
        for k in ("price", "unitprice"):
            v = parse_money(item.get(k))
            if v is not None:
                money.append(v)
                break
    return money, tau  # tau filled below from sub_total


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


def main():
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()
    ds = load_dataset("naver-clova-ix/cord-v2", split="test")
    print(f"CORD-v2 test size: {len(ds)}")

    results, t0 = [], time.time()
    for i, ex in enumerate(ds):
        img = ex["image"].convert("RGB") if hasattr(ex["image"], "convert") else ex["image"]
        px = processor(img, return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        dec = processor.tokenizer("<s_cord-v2>", add_special_tokens=False,
                                  return_tensors="pt").input_ids.to("cuda")
        with torch.inference_mode():
            out = model.generate(px, decoder_input_ids=dec, max_length=512, num_beams=1,
                                  early_stopping=True,
                                  pad_token_id=processor.tokenizer.pad_token_id)
        text = processor.batch_decode(out, skip_special_tokens=False)[0]
        pred = parse_donut_total(text)

        gt = json.loads(ex["ground_truth"]).get("gt_parse", {})
        gold_total = parse_money((gt.get("total") or {}).get("total_price"))
        money, _ = cord_money_lines(gt.get("menu"))
        sub = gt.get("sub_total") or {}
        tau = (parse_money(sub.get("tax_price")) or 0.0) + \
              (parse_money(sub.get("service_price")) or 0.0) - \
              (parse_money(sub.get("discount_price")) or 0.0)

        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold_total is not None
                   and abs(pred - gold_total) <= 0.02)
        results.append({"id": i, "pred": pred, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T)})

    n = len(results)
    correct_bare = sum(r["correct"] for r in results)
    accepted = [r for r in results if r["in_T"]]
    correct_strict = sum(r["correct"] for r in accepted)
    summary = {
        "n": n,
        "wall_sec": round(time.time() - t0, 1),
        "F1_bare": correct_bare / n,
        "accept_rate_sigma": len(accepted) / n,
        "F1_sigma_strict_on_accepted": correct_strict / max(1, len(accepted)),
        "delta_F1": (correct_strict / max(1, len(accepted))) - (correct_bare / n),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
