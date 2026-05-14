"""DONUT-SROIE on canonical SROIE Task-3 → I3 with PRECISE tau extraction v12.

v12 = v11 + two changes informed by L's failure-mode breakdown (146 of 220
applicable misses were tau_too_large, 70% theoretical recoverability):

  v12.fix_1  Total-line dominance.
    Lines matching the total/subtotal/incl/inclusive/sales/grand/cash/change/
    balance/paid family are dropped ENTIRELY — not consumed as tau contributors,
    not added to money_lines. This prevents 'Total (Incl. GST) RM 7.20' from
    being eaten as a tau=7.20 contribution (which was the dominant mechanism
    behind tau ≈ 2π in v11).

  v12.fix_2  Single tau per category, then sum across categories.
    Old: tau += sign * amt for every keyword match — SROIE receipts mention 'GST'
    on 2–3 lines so tau accumulated 2–3× the true tax.
    New: collect candidates grouped by name (tax / service / discount). Within
    each group take the LAST candidate (Malaysian receipts print the GST summary
    table near the bottom). Then sum across distinct categories.

All v9–v11 fixes retained: percent-skip, RM-prefix preference, decimal preference,
registration-pattern rejection, |tau|>10000 cap, multi-line look-ahead, bare-int
>=1000 rejection.

The I3 subset-sum, cardinality guard, eps tolerance, and DP are UNCHANGED.
Methodology is identical to v9/v10/v11; v12 only tightens tau extraction.
"""
import gc, json, os, re, sys, time
from collections import defaultdict
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
TAU_CAP = 10000.0
BARE_INT_REJECT_THRESHOLD = 1000.0


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


MONEY_TOKEN_RE = re.compile(
    r"(?P<cur>RM\s*|rm\s*|\$\s*)?(?P<num>-?\d+(?:\.\d{1,2})?)",
    re.I,
)

REG_AFTER_KW_RE = re.compile(
    r"\b(?:tax|gst|sst|vat|service|discount|rebate)\b\W{0,3}"
    r"(?:invoice|inv|no\.?|number|num|reg(?:istration)?|id|ref(?:erence)?|code)\b",
    re.I,
)

TAX_KW_RE  = re.compile(r"\b(tax|gst|sst|vat)\b", re.I)
SERV_KW_RE = re.compile(r"\bservice(?:\s*charge)?\b", re.I)
DISC_KW_RE = re.compile(r"\b(discount|rebate)\b", re.I)

# v12: TOTAL_LIKE matches receipt totals/cash/change/subtotal/incl lines. These
# are dropped entirely (not money, not tau). Applied BEFORE tax-keyword logic so
# 'Total (Incl. GST) 7.20' doesn't get eaten as a tau=7.20 contribution.
TOTAL_LIKE_RE = re.compile(
    r"\b(total|sub.?total|grand|incl|inclusive|nett?|sales|paid|tendered?|cash|change|balance|amount\s+due)\b",
    re.I,
)


def _scan_money_after(rest):
    for tok in MONEY_TOKEN_RE.finditer(rest):
        num_s = tok.group("num")
        end = tok.end()
        tail2 = rest[end:end + 2].lstrip()
        if tail2.startswith("%"):
            continue
        try:
            v = float(num_s)
        except ValueError:
            continue
        has_cur = bool(tok.group("cur"))
        has_dec = "." in num_s
        if not has_cur and not has_dec and abs(v) >= BARE_INT_REJECT_THRESHOLD:
            continue
        yield v, has_cur, has_dec, end


def _pick_amount(rest):
    cands = list(_scan_money_after(rest))
    if not cands:
        return None
    cur = [c for c in cands if c[1]]
    if cur:
        return cur[-1][0]
    dec = [c for c in cands if c[2]]
    if dec:
        return dec[-1][0]
    return cands[-1][0]


def _extract_amount(line, kw_re, next_line=None):
    if REG_AFTER_KW_RE.search(line):
        return None
    m = kw_re.search(line)
    if not m:
        return None
    rest = line[m.end():]
    val = _pick_amount(rest)
    if val is not None:
        return val
    if next_line is None:
        return None
    return _pick_amount(next_line)


def extract_money_lines(text_lines):
    """v12: total-line dominance + single-candidate-per-category tau pick."""
    money = []
    tax_candidates = []  # list of (sign, amt, name, line_text); grouped+picked below
    n = len(text_lines)
    for i, ln in enumerate(text_lines):
        nxt = text_lines[i + 1] if i + 1 < n else None

        # v12.fix_1: drop total/incl/sales/cash/change/etc. lines ENTIRELY.
        # These are receipt-summary lines, neither item amounts nor tax amounts.
        if TOTAL_LIKE_RE.search(ln):
            continue

        consumed_as_tax = False
        for kw_re, sign, name in (
            (TAX_KW_RE,  +1, "tax"),
            (SERV_KW_RE, +1, "service"),
            (DISC_KW_RE, -1, "discount"),
        ):
            if kw_re.search(ln):
                amt = _extract_amount(ln, kw_re, nxt)
                if amt is not None:
                    tax_candidates.append((sign, amt, name, ln.strip()[:60]))
                consumed_as_tax = True
                break
        if consumed_as_tax:
            continue

        v = parse_money_strict(ln)
        if v is None: continue
        money.append(v)

    # v12.fix_2: group candidates by category, pick LAST within each, sum across.
    by_name = defaultdict(list)
    for sign, amt, name, ln_str in tax_candidates:
        by_name[name].append((sign, amt, ln_str))
    tau = 0.0
    diag = []
    for name, cands in by_name.items():
        sign, amt, ln_str = cands[-1]
        tau += sign * amt
        diag.append((name, ln_str, amt))

    capped = abs(tau) > TAU_CAP
    if capped:
        print(f"  [tau-cap] dropping runaway tau={tau:.2f}; contributors={diag}")
        tau = 0.0
    return money[:MAX_MONEY], tau, capped


def I3_reachable(money_lines, tau, eps=0.02):
    """UNCHANGED from v9: 0/1-knapsack DP, cardinality guard |S|>=kmin."""
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
    cap_fires = 0
    for (stem, _), text in zip(items, all_text):
        pred = parse_total(text)
        gold = load_gold_total(stem, ent_dir)
        ocr_lines = sroie_ocr.get(stem, [])
        money, tau, capped = extract_money_lines(ocr_lines)
        if capped: cap_fires += 1
        T = I3_reachable(money, tau) if money else set()
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold is not None and abs(pred - gold) <= 0.02)
        results.append({"id": stem, "pred": pred, "gold": gold, "in_T": in_T,
                        "correct": correct, "T_size": len(T),
                        "money_count": len(money), "tau": tau,
                        "ocr_lines": len(ocr_lines)})

    for r in results:
        assert abs(r["tau"]) <= TAU_CAP, f"tau cap failed on {r['id']}: tau={r['tau']}"

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    gold_ok = sum(1 for r in results if r["gold"] is not None)
    ocr_lines_mean = sum(r["ocr_lines"] for r in results) / n
    money_count_mean = sum(r["money_count"] for r in results) / n
    tau_abs_sorted = sorted(abs(r["tau"]) for r in results)
    tau_abs_median = tau_abs_sorted[n // 2]
    tau_abs_mean = sum(abs(r["tau"]) for r in results) / n
    summary = {
        "checkpoint": CKPT, "corpus": "canonical SROIE Task-3", "mirror": mirror,
        "setup": "in-distribution",
        "ocr_source": "darentang/sroie Task-1",
        "tau_extraction": "v12_total_line_dominance_single_tau_per_category",
        "n": len(results), "batch_size": BATCH,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n, "gold_ok_rate": gold_ok / n,
        "ocr_lines_per_receipt_mean": ocr_lines_mean,
        "money_lines_per_receipt_mean": money_count_mean,
        "tau_abs_median": tau_abs_median,
        "tau_abs_mean": tau_abs_mean,
        "tau_cap_fires": cap_fires,
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
