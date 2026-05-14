"""DONUT-CORD on SROIE-347 → I3 before/after F1 (cross-corpus end-task).

Paper 1 (FOCUS-Sigma) end-task validation. Cross-corpus regime: a CORD-trained Donut
on Malaysian retail receipts. Tests whether I3 subset-sum verification lifts F1 on a
public, reviewer-recognisable baseline.

Runtime target: ~2.5 min on RTX 4090.
Success: F1_sigma_strict_on_accepted - F1_bare ≥ +0.02.
"""
import json, os, re, time
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
SROIE_HF = os.environ.get("SROIE_HF", "darentang/sroie")
OUT = Path("runs/A_donut_cord_on_sroie.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_donut_total(text):
    for tag in ("<s_total>", "<s_total_price>", "<s_total.total_price>"):
        m = re.search(re.escape(tag) + r"([^<]+)", text)
        if m:
            return parse_money(m.group(1))
    return None


DROP_KW = re.compile(r"\b(total|sub.?total|cash|change|paid|balance|tendered?)\b", re.I)
TAX_KW  = re.compile(r"\b(tax|gst|sst|vat)\b", re.I)
SERV_KW = re.compile(r"\b(service)\b", re.I)
DISC_KW = re.compile(r"\b(discount|rebate)\b", re.I)


def extract_money_lines(text_lines):
    money, tau = [], 0.0
    for ln in text_lines:
        v = parse_money(ln)
        if v is None:
            continue
        if TAX_KW.search(ln) or SERV_KW.search(ln):
            tau += v
        elif DISC_KW.search(ln):
            tau -= v
        elif DROP_KW.search(ln):
            continue
        else:
            money.append(v)
    return money, tau


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

    ds = load_dataset(SROIE_HF, split="test", trust_remote_code=True)
    print(f"SROIE test size: {len(ds)}")
    sample = ds[0]
    print(f"Schema keys: {list(sample.keys())[:10]}")

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

        # ADAPT: SROIE schemas vary across HF mirrors.
        gold_total = parse_money(
            ex.get("total") or ex.get("gold", {}).get("total")
            or (ex.get("label") or {}).get("total")
        )
        text_lines = ex.get("words") or ex.get("text") or ex.get("ocr") or []
        if isinstance(text_lines, str): text_lines = text_lines.split("\n")

        money, tau = extract_money_lines(text_lines)
        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold_total is not None
                   and abs(pred - gold_total) <= 0.02)
        results.append({"id": i, "pred": pred, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T),
                        "money_count": len(money), "tau": tau})
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(ds)}  elapsed={time.time()-t0:.0f}s")

    n = len(results)
    correct_bare = sum(r["correct"] for r in results)
    accepted = [r for r in results if r["in_T"]]
    correct_strict = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    summary = {
        "n": n,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n,
        "F1_bare": correct_bare / n,
        "accept_rate_sigma": len(accepted) / n,
        "F1_sigma_strict_on_accepted": correct_strict / max(1, len(accepted)),
        "delta_F1": (correct_strict / max(1, len(accepted))) - (correct_bare / n),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
