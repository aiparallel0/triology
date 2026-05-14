"""DONUT-SROIE on canonical SROIE Task-3 → I3 with PRECISE tau extraction v13.

v13 = v12 + multi-candidate tau (genuine method extension, not just extractor):

  v13.fix_1  Multi-candidate tau. Instead of picking ONE tau and running DP once,
    collect ALL plausible tau candidates (tau=0, v12's per-category-last-then-sum,
    each individual extractor candidate). Run DP once over money_lines; check
    whether pi matches any subset-sum + any candidate tau. The acceptance rule is:

        sigma fires iff exists tau_k in candidates, exists S subset money_lines
        with |S| >= kmin(tau_k) and sum(S) + tau_k approx= pi.

    Mathematically, this is I3 with tau treated as a set rather than a scalar.

All v9-v12 extractor fixes retained: percent-skip, currency-prefix preference,
decimal preference, registration-pattern rejection, bare-int>=1000 rejection,
TOTAL_LIKE dominance, multi-line look-ahead, |tau|<=10000 cap.

The I3 DP and cardinality guard are UNCHANGED. v13 changes the tau extraction
from 'single estimate' to 'set of candidates' and the acceptance rule from
'pi matches T(money, tau)' to 'pi matches the union of T(money, tau_k)'.

Backwards compatibility: extract_money_lines() returns the v12 (money, tau, capped)
tuple so G and L diagnostics keep working. Use extract_money_lines_v13() for the
full multi-candidate behavior (returns (money, candidates, raw)).
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
MAX_TAU_CANDIDATES = 8
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


def _scan_money_and_tax(text_lines):
    """Internal: parse all lines once. Returns (money, raw_tax_candidates).

    money: list of money values from non-tax, non-total-only lines
    raw_tax_candidates: list of (sign, amt, name, line_text) tuples
    """
    money = []
    raw = []
    n = len(text_lines)
    for i, ln in enumerate(text_lines):
        nxt = text_lines[i + 1] if i + 1 < n else None
        if TOTAL_LIKE_RE.search(ln) and not (TAX_KW_RE.search(ln) or SERV_KW_RE.search(ln) or DISC_KW_RE.search(ln)):
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
                    raw.append((sign, amt, name, ln.strip()[:60]))
                consumed_as_tax = True
                break
        if consumed_as_tax:
            continue
        v = parse_money_strict(ln)
        if v is None: continue
        money.append(v)
    return money[:MAX_MONEY], raw


def extract_money_lines_v13(text_lines):
    """v13 multi-candidate interface. Returns (money, tau_candidates, raw)."""
    money, raw = _scan_money_and_tax(text_lines)
    cands = {0.0}
    by_name = defaultdict(list)
    for sign, amt, name, _ in raw:
        by_name[name].append((sign, amt))
    if by_name:
        tau_v12 = 0.0
        for name, items in by_name.items():
            sign, amt = items[-1]
            tau_v12 += sign * amt
        cands.add(round(tau_v12, 4))
    for sign, amt, _, _ in raw:
        cands.add(round(sign * amt, 4))
    cands = [t for t in cands if abs(t) <= TAU_CAP]
    if len(cands) > MAX_TAU_CANDIDATES:
        cands_sorted = sorted(cands, key=lambda t: -abs(t))
        cands = list(set([0.0] + cands_sorted[:MAX_TAU_CANDIDATES - 1]))
    return money, cands, raw


def extract_money_lines(text_lines):
    """v12-compatible single-tau interface, kept for G/L diagnostics.
    Returns (money, tau_scalar, capped). Uses per-category-last-then-sum aggregation.
    """
    money, raw = _scan_money_and_tax(text_lines)
    by_name = defaultdict(list)
    for sign, amt, name, _ in raw:
        by_name[name].append((sign, amt))
    tau = 0.0
    for name, items in by_name.items():
        sign, amt = items[-1]
        tau += sign * amt
    capped = abs(tau) > TAU_CAP
    if capped:
        tau = 0.0
    return money, tau, capped


def I3_reachable_multi(money_lines, tau_candidates, eps=0.02):
    """v13: union of T sets across all tau candidates."""
    if not money_lines or not tau_candidates:
        return set()
    cents = [int(round(v * 100)) for v in money_lines]
    D = {0: 0}
    for v in cents:
        new = dict(D)
        for s, k in D.items():
            ns = s + v
            if ns not in new or new[ns] > k + 1: new[ns] = k + 1
        D = new
    T = set()
    for tau in tau_candidates:
        kmin = 1 if abs(tau) > eps else 2
        tau_c = int(round(tau * 100))
        for s, k in D.items():
            if k >= kmin:
                T.add((s + tau_c) / 100.0)
    return T


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
    n_candidates_total = 0
    for (stem, _), text in zip(items, all_text):
        pred = parse_total(text)
        gold = load_gold_total(stem, ent_dir)
        ocr_lines = sroie_ocr.get(stem, [])
        money, tau_cands, _raw = extract_money_lines_v13(ocr_lines)
        n_candidates_total += len(tau_cands)
        T = I3_reachable_multi(money, tau_cands)
        in_T = pred is not None and any(abs(pred - t) <= 0.02 for t in T)
        correct = (pred is not None and gold is not None and abs(pred - gold) <= 0.02)
        # v12 single-tau pick for downstream L diagnostic compat
        tau_single = max(tau_cands, key=abs) if len(tau_cands) > 1 else (tau_cands[0] if tau_cands else 0.0)
        results.append({"id": stem, "pred": pred, "gold": gold, "in_T": in_T,
                        "correct": correct, "T_size": len(T),
                        "money_count": len(money),
                        "n_tau_candidates": len(tau_cands),
                        "tau_candidates": tau_cands,
                        "tau": tau_single,
                        "ocr_lines": len(ocr_lines)})

    n = max(1, len(results))
    accepted = [r for r in results if r["in_T"]]
    correct_all = sum(r["correct"] for r in results)
    correct_accepted = sum(r["correct"] for r in accepted)
    parser_ok = sum(1 for r in results if r["pred"] is not None)
    gold_ok = sum(1 for r in results if r["gold"] is not None)
    money_count_mean = sum(r["money_count"] for r in results) / n
    cand_mean = n_candidates_total / n
    summary = {
        "checkpoint": CKPT, "corpus": "canonical SROIE Task-3", "mirror": mirror,
        "setup": "in-distribution",
        "ocr_source": "darentang/sroie Task-1",
        "tau_extraction": "v13_multi_candidate_tau_union_T",
        "n": len(results), "batch_size": BATCH,
        "wall_sec": round(time.time() - t0, 1),
        "parser_ok_rate": parser_ok / n, "gold_ok_rate": gold_ok / n,
        "money_lines_per_receipt_mean": money_count_mean,
        "tau_candidates_per_receipt_mean": cand_mean,
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
