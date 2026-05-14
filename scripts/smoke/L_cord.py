"""L_cord: sigma failure-mode taxonomy on CORD-v2 (mirror of L on SROIE).

Reviewer attack defended: 'your failure-mode analysis is SROIE-specific; CORD's
failures might tell a different story.'

For each CORD receipt, re-extract items + total + tax from gt_parse and classify
the sigma decision into:
  - success
  - pred_wrong (model output wrong, not sigma's fault)
  - tau_too_large (target = pi - tau < 0; never reachable)
  - tau_too_negative (target > sum_money + eps; not reachable)
  - close_miss (best feasible subset within 1.0 of target)
  - far_miss (best feasible subset > 1.0 from target; structural ceiling)
  - no_money / no_feasible_subsets
  - should_have_fired (assertion: best_dist within eps but in_T was false)

Compare counts to L's SROIE distribution. CORD is the labeled-amounts regime;
failure modes should skew differently (less far_miss, more close_miss if any).

Reads B's per-receipt predictions. CPU only. ~5 sec.
"""
import json
from collections import defaultdict, Counter
from pathlib import Path

from datasets import load_dataset

RUNS = Path("runs")
B_OUT = RUNS / "B_donut_cord_on_cord.json"
OUT = RUNS / "L_cord_failure_modes.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

EPS = 0.02
CLOSE_THRESHOLD = 1.0


def parse_money(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


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
    tax = parse_money(total_info.get("tax_price")) if isinstance(total_info, dict) else None
    return items, total, (tax if tax is not None else 0.0)


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
    if not B_OUT.exists():
        OUT.write_text(json.dumps({"available": False, "reason": "B output missing"}, indent=2))
        print("B's runs/B_donut_cord_on_cord.json not found"); return
    b = json.loads(B_OUT.read_text())
    b_results = {r["id"]: r for r in b.get("results", [])}

    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    print(f"CORD test n={len(ds)}")

    per_receipt = []
    for ex_idx in range(len(ds)):
        items, total, tau = extract_cord(ds[ex_idx])
        items = items or []
        if tau is None: tau = 0.0
        r = b_results.get(ex_idx, {})
        pred = r.get("pred")
        gold = r.get("gold")
        correct = r.get("correct", False)
        in_T = r.get("in_T", False)

        mc = len(items)
        sum_money = sum(items) if items else 0.0
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
            if not items:
                category = "no_money"
            elif target < -EPS:
                category = "tau_too_large"
            elif target > sum_money + EPS:
                category = "tau_too_negative"
            else:
                feasible = subset_sums_with_kmin(items, kmin)
                if not feasible:
                    category = "no_feasible_subsets"
                else:
                    target_c = int(round(target * 100))
                    best_dist_c = min(abs(s - target_c) for s in feasible)
                    best_dist = best_dist_c / 100.0
                    if best_dist <= EPS:
                        category = "should_have_fired"
                    elif best_dist <= CLOSE_THRESHOLD:
                        category = "close_miss"
                    else:
                        category = "far_miss"

        per_receipt.append({
            "id": ex_idx, "bucket": bucket, "category": category,
            "pred": pred, "gold": gold, "tau": tau, "money_count": mc,
            "sum_money": sum_money, "target": target, "best_dist": best_dist,
        })

    by_cat = Counter(r["category"] for r in per_receipt)
    by_bucket_cat = defaultdict(lambda: Counter())
    for r in per_receipt:
        by_bucket_cat[r["bucket"]][r["category"]] += 1

    applicable = [r for r in per_receipt
                  if r["bucket"] in ("2-4", "5-9")
                  and r["category"] not in ("no_pred", "pred_wrong")]
    n_app = len(applicable)
    fires = sum(1 for r in applicable if r["category"] == "success")
    misses_by_cat = Counter(r["category"] for r in applicable if r["category"] != "success")

    summary = {
        "corpus": "CORD-v2 test",
        "n_total": len(per_receipt),
        "counts_by_category": dict(by_cat),
        "counts_by_bucket_category": {b: dict(c) for b, c in by_bucket_cat.items()},
        "applicable_2_9_correct": {
            "n": n_app, "fires": fires,
            "current_coverage_on_applicable": fires / max(1, n_app),
            "misses_breakdown": dict(misses_by_cat),
        },
        "note": (
            "Mirror of L on CORD. Compare to L's SROIE breakdown: if CORD's failures concentrate "
            "in close_miss/should_have_fired while SROIE's concentrate in tau_too_negative/far_miss, "
            "the regime distinction (labeled vs OCR) is empirically grounded at the failure-mode "
            "level too. CORD's failures are tolerance/rounding-driven; SROIE's are extractor/OCR-driven."
        ),
    }
    OUT.write_text(json.dumps({"summary": summary, "per_receipt": per_receipt}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
