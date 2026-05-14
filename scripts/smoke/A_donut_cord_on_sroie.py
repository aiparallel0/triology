"""DONUT-CORD on SROIE → I3 selective prediction (cross-corpus end-task) v4.

v4 changes vs v3:
  - STRICT money parser: requires decimal point or currency symbol
    (rejects address numbers, phone numbers, dates)
  - Cap money_lines at 15 to prevent DP memory blow-up
  - SROIE_LIMIT env var (default 200) to cap receipts processed
  - Periodic gc.collect() + torch.cuda.empty_cache() every 25 receipts

Runtime: ~2 min on RTX 4090 (200 receipts × ~0.5s each).
Note: zzzDavid's repo is the SROIE TRAIN pool (626 receipts), not the
canonical 347 test set. Smoke test samples from the training pool;
canonical-test eval is deferred to camera-ready via Metric-AI/icdar_sroie.
"""
import gc, json, os, re, subprocess, sys, time
from pathlib import Path

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

CKPT = "naver-clova-ix/donut-base-finetuned-cord-v2"
SROIE_REPO = "https://github.com/zzzDavid/ICDAR-2019-SROIE.git"
SROIE_DIR = Path(os.environ.get("SROIE_DIR", "data/sroie_clone"))
SROIE_LIMIT = int(os.environ.get("SROIE_LIMIT", "200"))
MAX_MONEY_LINES = 15
OUT = Path("runs/A_donut_cord_on_sroie.json")
OUT.parent.mkdir(parents=True, exist_ok=True)


def parse_money(s):
    """Lenient parse — for gold totals from key files."""
    if s is None: return None
    s = str(s).replace(",", "").replace("RM", "").replace("$", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def parse_money_strict(s):
    """STRICT parse — only counts as money if it has currency or decimal.

    Filters out: address numbers (123 Main St), phone numbers (12345678),
    dates (01/15/2024), item counts (1 x Coffee).
    Keeps: 23.45, RM 12.50, $10.99, 8.50.
    """
    if s is None: return None
    s = str(s).strip()
    has_currency = ("RM" in s.upper()) or ("$" in s)
    s_no_curr = s.replace("RM", "").replace("rm", "").replace("$", "").replace(",", "").strip()
    has_decimal = bool(re.search(r"\d+\.\d{1,2}\b", s_no_curr))
    if not (has_currency or has_decimal):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s_no_curr)
    return float(m.group()) if m else None


def parse_donut_total(text):
    for tag in ("<s_total.total_price>", "<s_total_price>", "<s_total>"):
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


def ensure_sroie_clone():
    if not SROIE_DIR.exists():
        print(f"Cloning {SROIE_REPO} ...")
        SROIE_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth=1", SROIE_REPO, str(SROIE_DIR)], check=True)
    for img_dir in [SROIE_DIR / "data" / "img",
                    SROIE_DIR / "data" / "test" / "img",
                    SROIE_DIR / "img"]:
        if img_dir.exists() and any(img_dir.glob("*.jpg")):
            return img_dir, img_dir.parent
    raise RuntimeError(f"No SROIE images found under {SROIE_DIR}")


def load_gold_total(stem, data_root):
    for sub in ("key", "entities"):
        for ext in ("json", "txt"):
            path = data_root / sub / f"{stem}.{ext}"
            if not path.exists(): continue
            text = path.read_text(errors="ignore").strip()
            if not text: continue
            try:
                data = json.loads(text)
                if isinstance(data, dict) and "total" in data:
                    return parse_money(data["total"])
            except json.JSONDecodeError:
                for line in text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        if k.strip().lower() == "total":
                            return parse_money(v.strip())
    return None


def load_ocr_lines(stem, data_root):
    for ext in ("txt", "csv"):
        path = data_root / "box" / f"{stem}.{ext}"
        if not path.exists(): continue
        lines = []
        for line in path.read_text(errors="ignore").splitlines():
            parts = line.split(",", 8)
            if len(parts) >= 9:
                lines.append(parts[8])
        return lines
    return []


def main():
    img_dir, data_root = ensure_sroie_clone()
    images = sorted(img_dir.glob("*.jpg"))[:SROIE_LIMIT]
    print(f"SROIE: {len(images)} of {len(list(img_dir.glob('*.jpg')))} (limit={SROIE_LIMIT})")

    processor = DonutProcessor.from_pretrained(CKPT)
    model = VisionEncoderDecoderModel.from_pretrained(CKPT, torch_dtype=torch.float16).to("cuda").eval()

    results, t0 = [], time.time()
    for i, img_path in enumerate(images):
        stem = img_path.stem
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  skip {stem}: {e}"); continue
        gold_total = load_gold_total(stem, data_root)
        text_lines = load_ocr_lines(stem, data_root)

        px = processor(img, return_tensors="pt").pixel_values.to("cuda", dtype=torch.float16)
        dec = processor.tokenizer("<s_cord-v2>", add_special_tokens=False,
                                  return_tensors="pt").input_ids.to("cuda")
        with torch.inference_mode():
            out = model.generate(px, decoder_input_ids=dec, max_length=512, num_beams=1,
                                  pad_token_id=processor.tokenizer.pad_token_id)
        text = processor.batch_decode(out, skip_special_tokens=False)[0]
        pred = parse_donut_total(text)

        money, tau = extract_money_lines(text_lines)
        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold_total is not None
                   and abs(pred - gold_total) <= 0.02)

        if i == 0:
            print(f"  [sanity] stem={stem} pred={pred} gold={gold_total} "
                  f"|money|={len(money)} |T|={len(T)} tau={tau:.2f} in_T={in_T}")

        results.append({"id": stem, "pred": pred, "gold": gold_total,
                        "in_T": in_T, "correct": correct, "T_size": len(T),
                        "money_count": len(money), "tau": tau})
        if (i + 1) % 25 == 0:
            gc.collect(); torch.cuda.empty_cache()
            print(f"  {i+1}/{len(images)}  elapsed={time.time()-t0:.0f}s")

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    gold_ok = sum(1 for r in results if r["gold"] is not None)
    summary = {
        "n": len(results),
        "sroie_limit": SROIE_LIMIT,
        "max_money_lines": MAX_MONEY_LINES,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n,
        "gold_ok_rate": gold_ok / n,
        "coverage_1.0_F1": correct_all / n,
        "coverage_sigma": len(accepted) / n,
        "sigma_F1_on_accepted": correct_accepted / max(1, len(accepted)),
        "sigma_recall_on_correct": (sum(1 for r in results if r["correct"] and r["in_T"])
                                    / max(1, correct_all)),
        "sigma_precision": correct_accepted / max(1, len(accepted)),
        "note": ("cross-corpus DONUT-CORD on SROIE: expect low coverage_1.0_F1 due to "
                 "output-format mismatch (CORD trains on IDR integers, SROIE prints RM decimals)."),
    }
    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
