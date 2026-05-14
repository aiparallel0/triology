"""L: SROIE failure-mode analysis — mechanically categorize why sigma misses on correct preds.

For each of the 347 SROIE receipts:
  1. Read A's prediction log (runs/A_donut_cord_on_sroie.json).
  2. Re-extract money_lines + tau via the same A extractor (v11).
  3. For every receipt where pred is correct but in_T is false, compute target = pred - tau
     and categorize the miss:
       - tau_too_large    : target < -eps (negative target unreachable)
       - tau_too_negative : target > sum(money) + eps (target exceeds capacity)
       - close_miss       : nearest feasible subset is within 1.0 of target
       - far_miss         : nearest feasible subset > 1.0 from target
       - no_money         : extractor produced no money lines
       - should_have_fired: nearest subset within eps but in_T was false (assertion bug)
  4. Aggregate counts per category and per money_count bucket.

L identifies the dominant failure mode so extractor effort goes where it has ROI:
  - tau_too_large dominant         => keep tightening tau extractor
  - close_miss dominant            => money_lines noisy; filter non-item rows harder
  - far_miss dominant              => fundamental data limit; coverage ceiling reached

CPU-only post-processing. Runtime ~10-30 s. Reads A's results, no model loading.
"""
import json, os, sys
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent))
from sroie_canonical import ensure_canonical_test_set, load_sroie_ocr_lines  # noqa
from A_donut_cord_on_sroie import extract_money_lines, TAU_CAP  # noqa

DATA = Path(os.environ.get("SROIE_DATA", "data/sroie_canonical"))
A_OUT = Path("runs/A_donut_cord_on_sroie.json")
OUT = Path("runs/L_sroie_failure_modes.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
EPS = 0.02
CLOSE_THRESHOLD = 1.0


def bucket_of(mc):
    if mc == 0: return "0"
    if mc == 1: return "1"
    if mc <= 4: return "2-4"
    if mc <= 9: return "5-9"
    return ">=10"


def subset_sums_with_kmin(money, kmin):
    cents = [int(round(v * 100)) for v in money]
    D = {0: 0}
    for v in cents:
        new = dict(D)
        for s, k in D.items():
            ns = s + v
            if ns not in new or new[ns] > k + 1: new[ns] = k + 1
        D = new
    return [s for s, k in D.items() if k >= kmin]


def main():
    if not A_OUT.exists():
        print("L requires runs/A_donut_cord_on_sroie.json; skipping.")
        OUT.write_text(json.dumps({"available": False, "reason": "A output missing"}, indent=2))
        return
    a = json.loads(A_OUT.read_text())
    a_results = {r["id"]: r for r in a.get("results", [])}

    _, img_dir, _ = ensure_canonical_test_set(DATA)
    paths = sorted(img_dir.glob("*.jpg"))
    stems = {p.stem for p in paths}
    ocr = load_sroie_ocr_lines(stems)
    print(f"Loaded OCR for {len(ocr)}/{len(stems)} stems; A results for {len(a_results)}")

    per_receipt = []
    for stem in sorted(a_results.keys()):
        r = a_results[stem]
        pred = r.get("pred")
        gold = r.get("gold")
        correct = r.get("correct", False)
        in_T = r.get("in_T", False)

        lines = ocr.get(stem, [])
        money, tau, capped = extract_money_lines(lines)
        mc = len(money)
        sum_money = sum(money) if money else 0.0
        bucket = bucket_of(mc)

        target = None
        best_dist = None
        category = None

        if pred is None:
            category = "no_pred"
        elif not correct:
            category = "pred_wrong"
        elif in_T:
            category = "success"
        else:
            target = pred - tau
            kmin = 1 if abs(tau) > EPS else 2
            if not money:
                category = "no_money"
            elif target < -EPS:
                category = "tau_too_large"
            elif target > sum_money + EPS:
                category = "tau_too_negative"
            else:
                feasible_cents = subset_sums_with_kmin(money, kmin)
                if not feasible_cents:
                    category = "no_feasible_subsets"
                else:
                    target_c = int(round(target * 100))
                    best_dist_c = min(abs(s - target_c) for s in feasible_cents)
                    best_dist = best_dist_c / 100.0
                    if best_dist <= EPS:
                        category = "should_have_fired"
                    elif best_dist <= CLOSE_THRESHOLD:
                        category = "close_miss"
                    else:
                        category = "far_miss"

        per_receipt.append({
            "stem": stem, "bucket": bucket, "category": category,
            "pred": pred, "gold": gold, "tau": tau, "money_count": mc,
            "sum_money": sum_money, "target": target, "best_dist": best_dist,
            "capped": capped,
        })

    by_cat = Counter(c["category"] for c in per_receipt)
    by_bucket_cat = defaultdict(lambda: Counter())
    for c in per_receipt:
        by_bucket_cat[c["bucket"]][c["category"]] += 1

    applicable = [c for c in per_receipt
                  if c["bucket"] in ("2-4", "5-9")
                  and c["category"] not in ("no_pred", "pred_wrong")]
    n_app = len(applicable)
    fires = sum(1 for c in applicable if c["category"] == "success")
    misses_by_cat = Counter(c["category"] for c in applicable if c["category"] != "success")

    # Recoverability estimates: theoretical max coverage if we could fix each mode.
    recoverable_tau_too_large = misses_by_cat.get("tau_too_large", 0)
    recoverable_close_miss = misses_by_cat.get("close_miss", 0)
    recoverable_no_money = misses_by_cat.get("no_money", 0)

    # Among misses where tau looks suspicious (cap fired OR tau implausibly large for the pred):
    suspicious_tau_misses = sum(
        1 for c in applicable
        if c["category"] != "success"
        and (c["capped"] or (c["tau"] is not None and c["pred"] is not None
                             and abs(c["tau"]) > 2 * abs(c["pred"])))
    )

    summary = {
        "n_total": len(per_receipt),
        "counts_by_category": dict(by_cat),
        "counts_by_bucket_category": {b: dict(c) for b, c in by_bucket_cat.items()},
        "applicable_2_9_correct": {
            "n": n_app,
            "fires": fires,
            "current_coverage_on_applicable": fires / max(1, n_app),
            "misses_breakdown": dict(misses_by_cat),
            "suspicious_tau_misses": suspicious_tau_misses,
        },
        "recoverability_ceiling": {
            "if_fix_tau_too_large": (fires + recoverable_tau_too_large) / max(1, n_app),
            "if_fix_close_miss":    (fires + recoverable_close_miss) / max(1, n_app),
            "if_fix_no_money":      (fires + recoverable_no_money) / max(1, n_app),
            "if_fix_all_three":     (fires + recoverable_tau_too_large + recoverable_close_miss + recoverable_no_money) / max(1, n_app),
        },
        "tau_cap_fires": sum(1 for c in per_receipt if c["capped"]),
        "interpretation": (
            "Compare misses_breakdown counts. tau_too_large dominant => extractor still leaks reg-numbers "
            "or look-ahead overreach. close_miss dominant => money_lines contain non-items (subtotals, cash, change) "
            "that need stricter filtering. far_miss dominant => the receipt's printed line items don't reconstruct "
            "to (pred-tau) at all; this is the structural OCR ceiling and not extractor-fixable."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary, "per_receipt": per_receipt}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
