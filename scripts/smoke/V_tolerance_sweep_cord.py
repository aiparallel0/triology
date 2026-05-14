"""V: sigma epsilon-tolerance precision/coverage sweep on CORD-v2.

Reviewer attack defended: 'why epsilon=0.02? Your operating point is arbitrary.'

For each epsilon in {0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00, 5.00} re-run I3
on CORD with that tolerance, report (coverage, precision). Yields the sigma
precision/coverage curve as a function of tolerance. CORD has clean labeled
item amounts so the curve directly characterizes sigma's hyperparameter sensitivity.

Reads B's per-receipt (pi, correct) for the model output. Re-extracts money_lines
from gt_parse.menu (no new inference). Pure CPU. ~5 sec.

This adds an empirical figure (precision/coverage curve) without changing any existing
sigma claim — just defends the chosen epsilon as a sensible operating point on the curve.
"""
import json
from pathlib import Path

from datasets import load_dataset

RUNS = Path("runs")
B_OUT = RUNS / "B_donut_cord_on_cord.json"
OUT = RUNS / "V_tolerance_sweep_cord.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

EPS_VALUES = [0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00, 5.00]


def parse_money(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def i3_reachable(money, tau, eps):
    """Build subset-sum set T = {sum(S) + tau : |S| >= kmin}. Same DP as A v13."""
    if not money: return set()
    kmin = 1 if abs(tau) > eps else 2
    cents = [int(round(v * 100)) for v in money]
    tau_c = int(round(tau * 100))
    D = {0: 0}
    for v in cents:
        new = dict(D)
        for s, k in D.items():
            ns = s + v
            if ns not in new or new[ns] > k + 1: new[ns] = k + 1
        D = new
    return {(s + tau_c) / 100.0 for s, k in D.items() if k >= kmin}


def extract_cord(ex):
    """Get (items[], total_price, tax_price) from CORD gt_parse."""
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


def main():
    if not B_OUT.exists():
        OUT.write_text(json.dumps({"available": False, "reason": "B output missing"}, indent=2))
        print("B's runs/B_donut_cord_on_cord.json not found"); return
    b = json.loads(B_OUT.read_text())
    b_pred = {r["id"]: (r.get("pred"), r.get("correct", False)) for r in b.get("results", [])}

    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    print(f"CORD test n={len(ds)}")

    per_eps = {}
    for eps in EPS_VALUES:
        n_total = 0
        n_accepted = 0
        n_correct = 0
        n_correct_accepted = 0
        for ex_idx in range(len(ds)):
            items, total, tau = extract_cord(ds[ex_idx])
            if not items or total is None: continue
            pred, correct_flag = b_pred.get(ex_idx, (None, False))
            if pred is None: continue
            n_total += 1
            if correct_flag: n_correct += 1
            T = i3_reachable(items, tau, eps)
            in_T = any(abs(pred - t) <= eps for t in T)
            if in_T:
                n_accepted += 1
                if correct_flag: n_correct_accepted += 1
        per_eps[f"eps={eps}"] = {
            "eps": eps,
            "n": n_total,
            "coverage": n_accepted / max(1, n_total),
            "precision": n_correct_accepted / max(1, n_accepted) if n_accepted else None,
            "n_accepted": n_accepted,
            "n_correct_accepted": n_correct_accepted,
            "base_F1": n_correct / max(1, n_total),
        }

    summary = {
        "corpus": "CORD-v2 test",
        "eps_values": EPS_VALUES,
        "per_eps": per_eps,
        "note": (
            "Sigma tolerance sweep. At eps=0.01 (strict), coverage is lowest but precision should "
            "approach 1.0. As eps grows, coverage rises and precision can drop. The chosen eps=0.02 "
            "(used in A's headline) should sit at a knee of the curve where precision is still close "
            "to its eps=0.01 value but coverage has improved. This curve is the operating-point defense."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
