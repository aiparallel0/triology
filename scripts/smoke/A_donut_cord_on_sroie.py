"""DONUT-SROIE on canonical SROIE Task-3 → I3 with PRECISE tau extraction v9.

v9 fix: previous tau extraction was 'if line contains tax-keyword, add ALL its money to tau'.
This grabbed phone numbers on 'TAX INVOICE 102013...' lines and similar.
v9 uses position-aware regex: captures the value IMMEDIATELY following 'tax|gst|sst|vat'.

Expected: median tau drops from O(100-100K) to O(1-10), gold totals re-enter T,
sigma_coverage jumps from 4% to 30-50% range matching B and F.
"""
import gc, json, os, re, sys, time
from pathlib import Path

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

sys.path.insert(0, str(Path(__file__).parent))
from sroie_canonical import ensure_canonical_test_set, load_gold_total, load_sroie_ocr_lines  # noqa

CKPT = os.environ.get("DONUT_SROIE_CKPT", "philschmid/donut-base-sroie")
DATA = Path(os.environ.get("SROIE_DATA", "data/sroie_canonical"))
OUT = Path("runs/A_donut_cord_on_sroie.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
BATCH = int(os.environ.get("DONUT_BATCH", "8"))
MAX_MONEY = 15


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_money_strict(s):
    if s is None: return None
    s = str(s).strip()
    has_currency = ("RM" in s.upper()) or ("$" in s)
    s2 = s.replace("RM", "").replace("rm", "").replace("$", "").replace(",", "").strip()
    has_decimal = bool(re.search(r"\d+\.\d{1,2}\b", s2))
    if not (has_currency or has_decimal): return None
    m = re.search(r"-?\d+(?:\.\d+)?", s2)
    return float(m.group()) if m else None


def parse_total(text):
    m = re.search(r"<s_total>([^<]+)", text)
    return parse_money(m.group(1)) if m else None


# v9: PRECISE tau extraction — keyword + immediately-following value.
# Captures: "tax 5.50", "GST: 2.30", "TAX(6%) RM 1.50", "SST 4.50".
# Rejects: "Tax invoice no: 12345" (no decimal/currency), "Phone tel: 03-12345".
TAX_VALUE_RE = re.compile(
    r"\b(?:tax|gst|sst|vat)(?:[\s\(][^,\d]{0,15})?[\s:=]+(?:rm|\$)?\s*(-?\d+\.\d{1,2})\b",
    re.I,
)
SERV_VALUE_RE = re.compile(
    r"\bservice(?:\s*charge)?(?:[\s\(][^,\d]{0,15})?[\s:=]+(?:rm|\$)?\s*(-?\d+\.\d{1,2})\b",
    re.I,
)
DISC_VALUE_RE = re.compile(
    r"\b(?:discount|rebate)(?:[\s\(][^,\d]{0,15})?[\s:=]+(?:rm|\$)?\s*(-?\d+\.\d{1,2})\b",
    re.I,
)
# Lines to skip entirely (their values are summary lines, not items)
DROP_KW = re.compile(r"\b(total|sub.?total|cash|change|paid|balance|tendered?|amount\s+due)\b", re.I)


def extract_money_lines(text_lines):
    """v9: precise tau extraction. tau only captures value adjacent to tax/service/discount keyword."""
    money, tau = [], 0.0
    for ln in text_lines:
        # First: check for precise tax/service/discount value pattern.
        # If matched, the line contributes ONLY that value to tau, NOT to money_lines.
        tax_m = TAX_VALUE_RE.search(ln)
        serv_m = SERV_VALUE_RE.search(ln)
        disc_m = DISC_VALUE_RE.search(ln)
        if tax_m:
            try: tau += float(tax_m.group(1))
            except ValueError: pass
            continue
        if serv_m:
            try: tau += float(serv_m.group(1))
            except ValueError: pass
            continue
        if disc_m:
            try: tau -= float(disc_m.group(1))
            except ValueError: pass
            continue
        # Else: regular money-line extraction.
        v = parse_money_strict(ln)
        if v is None: continue
        if DROP_KW.search(ln): continue
        money.append(v)
    # Sanity cap: tau shouldn't be absurd. If tau > 10000, it's likely a runaway match.
    if abs(tau) > 10000:
        tau = 0.0  # safer to drop than to poison T
    return money[:MAX_MONEY], tau


def I3_reachable(money_lines, tau, eps=0.02):
    kmin = 1 if abs(tau) > eps else 2
    cents = [int(round(v * 100)) for v in money_lines]
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
    mirror, img_dir, ent_dir = ensure_canonical_test_set(DATA)
    paths = sorted(img_dir.glob("*.jpg"))
    print(f"SROIE canonical-{len(paths)} via mirror={mirror}")

    t0 = time.time()
    stems_needed = {p.stem for p in paths}
    sroie_ocr = load_sroie_ocr_lines(stems_needed)
    print(f"  matched {len(sroie_ocr)}/{len(paths)} stems with Task-1 OCR")
    if not sroie_ocr:
        print("  WARN: no Task-1 OCR")
        sroie_ocr = {p.stem: [] for p in paths}

    print(f"Loading {CKPT}...")
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()
    start_id = model.config.decoder_start_token_id
    if start_id is None:
        start_id = processor.tokenizer.convert_tokens_to_ids(["<s>"])[0]

    items = []
    for p in paths:
        try: items.append((p.stem, Image.open(p).convert("RGB")))
        except Exception: continue

    print(f"Batched DONUT (batch={BATCH}) on {len(items)} images...")
    t1 = time.time()
    all_text = []
    for i in range(0, len(items), BATCH):
        batch = items[i:i+BATCH]
        px = processor([im for _, im in batch], return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        with torch.inference_mode():
            out = model.generate(
                px, max_length=512, num_beams=1,
                pad_token_id=processor.tokenizer.pad_token_id,
                decoder_start_token_id=start_id,
            )
        all_text.extend(processor.batch_decode(out, skip_special_tokens=False))
        if (i // BATCH + 1) % 5 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {min(i+BATCH, len(items))}/{len(items)} elapsed={time.time()-t1:.0f}s")
    print(f"DONUT done in {time.time()-t1:.1f}s")

    results = []
    for (stem, _), text in zip(items, all_text):
        pred = parse_total(text)
        gold = load_gold_total(stem, ent_dir)
        ocr_lines = sroie_ocr.get(stem, [])
        money, tau = extract_money_lines(ocr_lines)
        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold is not None and abs(pred - gold) <= 0.02)
        results.append({"id": stem, "pred": pred, "gold": gold, "in_T": in_T,
                        "correct": correct, "T_size": len(T),
                        "money_count": len(money), "tau": tau,
                        "ocr_lines": len(ocr_lines)})

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    gold_ok = sum(1 for r in results if r["gold"] is not None)
    ocr_lines_mean = sum(r["ocr_lines"] for r in results) / n
    money_count_mean = sum(r["money_count"] for r in results) / n
    tau_abs_median = sorted(abs(r["tau"]) for r in results)[n // 2]
    tau_abs_mean = sum(abs(r["tau"]) for r in results) / n
    summary = {
        "checkpoint": CKPT, "corpus": "canonical SROIE Task-3", "mirror": mirror,
        "setup": "in-distribution",
        "ocr_source": "darentang/sroie Task-1",
        "tau_extraction": "v9_strict_position_aware",
        "n": len(results), "batch_size": BATCH,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n, "gold_ok_rate": gold_ok / n,
        "ocr_lines_per_receipt_mean": ocr_lines_mean,
        "money_lines_per_receipt_mean": money_count_mean,
        "tau_abs_median": tau_abs_median,
        "tau_abs_mean": tau_abs_mean,
        "coverage_1.0_F1": correct_all / n,
        "coverage_sigma": len(accepted) / n,
        "sigma_F1_on_accepted": correct_accepted / max(1, len(accepted)),
        "sigma_recall_on_correct": (sum(1 for r in results if r["correct"] and r["in_T"]) / max(1, correct_all)),
        "sigma_precision": correct_accepted / max(1, len(accepted)),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
