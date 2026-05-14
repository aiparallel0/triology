"""DONUT-SROIE on canonical SROIE Task-3 → I3 selective prediction (IN-DISTRIBUTION) v6.

v6 methodological fix: previous A was DONUT-CORD on SROIE, an unfair cross-corpus
setup (CORD-trained model emits IDR-style integers on Malaysian receipts with
decimals). That setup measured noise + broken upstream, not the verifier.

v6 uses philschmid/donut-base-sroie — the SROIE-finetuned Donut checkpoint that
the YT-Rex / Triology Paper 2 baseline cites — on the canonical 347-image
SROIE Task-3 test set. Same role as Script B, just on a second corpus.

With B (DONUT-CORD on CORD) and A v6 (DONUT-SROIE on SROIE), Paper 1 has
two in-distribution sigma characterizations across two corpora.

Runtime: ~3 min on RTX 4090.
Success: F1_sigma_strict_on_accepted > F1_bare — a clean precision gate.
"""
import gc, json, os, re, sys, time
from pathlib import Path

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

sys.path.insert(0, str(Path(__file__).parent))
from sroie_canonical import ensure_canonical_test_set, load_gold_total  # noqa

CKPT = os.environ.get("DONUT_SROIE_CKPT", "philschmid/donut-base-sroie")
DATA = Path(os.environ.get("SROIE_DATA", "data/sroie_canonical"))
OUT = Path("runs/A_donut_cord_on_sroie.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
MAX_MONEY_LINES = 15


def parse_money(s):
    if s is None: return None
    s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_money_strict(s):
    if s is None: return None
    s = str(s).strip()
    has_currency = ("RM" in s.upper()) or ("$" in s)
    s_no_curr = s.replace("RM", "").replace("rm", "").replace("$", "").replace(",", "").strip()
    has_decimal = bool(re.search(r"\d+\.\d{1,2}\b", s_no_curr))
    if not (has_currency or has_decimal):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s_no_curr)
    return float(m.group()) if m else None


def parse_donut_sroie_total(text):
    """SROIE Donut emits <s_total>X</s_total> tags."""
    for tag in ("<s_total>",):
        m = re.search(re.escape(tag) + r"([^<]+)", text)
        if m: return parse_money(m.group(1))
    return None


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
    return money[:MAX_MONEY_LINES], tau


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


def tesseract_lines(img):
    try:
        import pytesseract
    except ImportError:
        return None
    try:
        text = pytesseract.image_to_string(img)
    except Exception:
        return None
    return [ln for ln in text.splitlines() if ln.strip()]


def main():
    mirror, img_dir, ent_dir = ensure_canonical_test_set(DATA)
    print(f"SROIE canonical-347 ready via mirror={mirror}")
    images = sorted(img_dir.glob("*.jpg"))
    print(f"Images: {len(images)}")

    print(f"Loading checkpoint: {CKPT}")
    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()

    # Use model's configured start token (Bug 2 guard: don't resolve string-form on tokenizer).
    start_id = model.config.decoder_start_token_id
    if start_id is None:
        start_id = processor.tokenizer.convert_tokens_to_ids(["<s>"])[0]
    print(f"decoder_start_token_id = {start_id}")

    tesseract_available = tesseract_lines(Image.new("RGB", (100, 100))) is not None
    print(f"Tesseract OCR available: {tesseract_available}  (I3 verification {'enabled' if tesseract_available else 'skipped'})")

    results, t0 = [], time.time()
    for i, img_path in enumerate(images):
        stem = img_path.stem
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  skip {stem}: {e}"); continue
        gold_total = load_gold_total(stem, ent_dir)

        px = processor(img, return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        with torch.inference_mode():
            out = model.generate(
                px,
                max_length=512, num_beams=1,
                pad_token_id=processor.tokenizer.pad_token_id,
                decoder_start_token_id=start_id,
            )
        text = processor.batch_decode(out, skip_special_tokens=False)[0]
        pred = parse_donut_sroie_total(text)

        if tesseract_available:
            text_lines = tesseract_lines(img) or []
            money, tau = extract_money_lines(text_lines)
            T = I3_reachable(money, tau) if money else set()
            in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        else:
            money, tau, T, in_T = [], 0.0, set(), False

        correct = (pred is not None and gold_total is not None
                   and abs(pred - gold_total) <= 0.02)

        if i == 0:
            print(f"  [sanity] stem={stem} pred={pred} gold={gold_total} "
                  f"|money|={len(money)} |T|={len(T)} tau={tau:.2f} in_T={in_T} text={text[:80]!r}")

        results.append({"id": stem, "pred": pred, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T),
                        "money_count": len(money), "tau": tau})
        if (i + 1) % 50 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {i+1}/{len(images)}  elapsed={time.time()-t0:.0f}s")

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    gold_ok = sum(1 for r in results if r["gold"] is not None)
    summary = {
        "checkpoint": CKPT,
        "corpus": "canonical SROIE Task-3",
        "mirror": mirror,
        "setup": "in-distribution",
        "n": len(results),
        "tesseract_available": tesseract_available,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n,
        "gold_ok_rate": gold_ok / n,
        "coverage_1.0_F1": correct_all / n,
        "coverage_sigma": len(accepted) / n if tesseract_available else None,
        "sigma_F1_on_accepted": (correct_accepted / max(1, len(accepted))) if tesseract_available else None,
        "sigma_recall_on_correct": (sum(1 for r in results if r["correct"] and r["in_T"])
                                    / max(1, correct_all)) if tesseract_available else None,
        "sigma_precision": (correct_accepted / max(1, len(accepted))) if tesseract_available else None,
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
