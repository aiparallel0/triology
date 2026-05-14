"""DONUT-SROIE on canonical SROIE Task-3 → I3 with PROPER per-line OCR v8.

v8 methodology fix: replaces Tesseract OCR (noisy on Malaysian thermal-print
receipts) with **labeled Task-1 OCR words+bboxes from darentang/sroie**,
grouped by y-coordinate into lines. Same image set (canonical-347), but
the verifier now sees clean OCR instead of Tesseract approximations.

Expected: sigma_coverage jumps from 2.6% (v7) to 40-55% range, comparable
to B (CORD) and F (WildReceipt) which use labeled annotations directly.

Runtime target: ~3 min on RTX 4090 + ~10s darentang download (first run).
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


DROP_KW = re.compile(r"\b(total|sub.?total|cash|change|paid|balance|tendered?)\b", re.I)
TAX_KW  = re.compile(r"\b(tax|gst|sst|vat)\b", re.I)
SERV_KW = re.compile(r"\b(service)\b", re.I)
DISC_KW = re.compile(r"\b(discount|rebate)\b", re.I)


def extract_money_lines(text_lines):
    money, tau = [], 0.0
    for ln in text_lines:
        v = parse_money_strict(ln)
        if v is None: continue
        if TAX_KW.search(ln) or SERV_KW.search(ln): tau += v
        elif DISC_KW.search(ln): tau -= v
        elif DROP_KW.search(ln): continue
        else: money.append(v)
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
    print("Loading Task-1 OCR from darentang/sroie...")
    stems_needed = {p.stem for p in paths}
    sroie_ocr = load_sroie_ocr_lines(stems_needed)
    print(f"  matched {len(sroie_ocr)}/{len(paths)} stems with Task-1 OCR")
    if not sroie_ocr:
        print("  WARN: no Task-1 OCR; falling back to Tesseract")
        # Tesseract fallback
        try:
            import pytesseract
            from concurrent.futures import ProcessPoolExecutor
            def _tess_one(path_str):
                try:
                    img = Image.open(path_str).convert("RGB")
                    text = pytesseract.image_to_string(img)
                    return Path(path_str).stem, [ln for ln in text.splitlines() if ln.strip()]
                except Exception:
                    return Path(path_str).stem, []
            with ProcessPoolExecutor(max_workers=8) as ex:
                sroie_ocr = dict(ex.map(_tess_one, [str(p) for p in paths]))
            print(f"  Tesseract OCR done in {time.time()-t0:.1f}s")
        except Exception as e:
            print(f"  Tesseract fallback failed: {e}")
            sroie_ocr = {p.stem: [] for p in paths}

    print(f"Loading {CKPT}...")
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()
    start_id = model.config.decoder_start_token_id
    if start_id is None:
        start_id = processor.tokenizer.convert_tokens_to_ids(["<s>"])[0]

    items = []
    for p in paths:
        try:
            items.append((p.stem, Image.open(p).convert("RGB")))
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
    summary = {
        "checkpoint": CKPT, "corpus": "canonical SROIE Task-3", "mirror": mirror,
        "setup": "in-distribution",
        "ocr_source": "darentang/sroie Task-1" if sroie_ocr and len(sroie_ocr) > 100 else "tesseract_fallback",
        "n": len(results), "batch_size": BATCH,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n, "gold_ok_rate": gold_ok / n,
        "ocr_lines_per_receipt_mean": ocr_lines_mean,
        "money_lines_per_receipt_mean": money_count_mean,
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
