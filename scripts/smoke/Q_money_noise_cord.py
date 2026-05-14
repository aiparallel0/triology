"""Q: synthetic money_lines noise sensitivity on CORD.

Reviewer attack defended: 'sigma only works when amounts are perfectly labeled;
it will break under realistic OCR noise.'

Protocol: load CORD test, take gt_parse.menu[*].price (the labeled per-item
amounts). Apply controlled noise at varying rates and re-run sigma. Use B's
stored per-receipt predictions (pi) as the model output. Track sigma_precision
and sigma_coverage degradation as noise increases.

Noise types:
  digit_swap  swap a digit in a random item amount (4.50 -> 4.70)
  decimal_shift  multiply/divide an item by 10
  item_drop  remove a random item entirely
  item_add  add a spurious amount drawn from uniform[0, max_item]

Noise rate p in {0.0, 0.05, 0.1, 0.2, 0.4} = probability per item.

CPU only. ~10 sec.
"""
import json, os, random
from pathlib import Path

from datasets import load_dataset

RUNS = Path("runs")
B_OUT = RUNS / "B_donut_cord_on_cord.json"
OUT = RUNS / "Q_money_noise_cord.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

NOISE_RATES = [0.0, 0.05, 0.10, 0.20, 0.40]
SEEDS = [0, 1, 2]  # 3 seeds for noise injection


def parse_money(s):
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


def i3_reachable(money, tau, eps=0.02):
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


def inject_noise(items, rate, rng):
    """Apply noise to a list of item amounts at given rate."""
    if rate <= 0 or not items: return list(items)
    items = list(items)
    max_amt = max(items)
    out = []
    for v in items:
        if rng.random() < rate:
            choice = rng.choice(["digit_swap", "decimal_shift", "drop"])
            if choice == "drop":
                continue
            elif choice == "decimal_shift":
                v = v * rng.choice([10, 0.1])
            else:
                # Digit swap: perturb a random digit position by +/-1
                s = f"{v:.2f}"
                if len(s) > 1:
                    pos = rng.randint(0, len(s) - 1)
                    if s[pos].isdigit():
                        new_d = (int(s[pos]) + rng.choice([-1, 1])) % 10
                        s = s[:pos] + str(new_d) + s[pos+1:]
                v = parse_money(s) or v
        out.append(v)
    # Random spurious addition
    if rng.random() < rate:
        out.append(rng.uniform(0, max_amt))
    return out


def extract_cord_items(ex):
    """Get item prices and total/tax from CORD ground_truth."""
    gt = ex.get("ground_truth")
    if isinstance(gt, str):
        try: gt = json.loads(gt)
        except Exception: return None, None, None
    if not isinstance(gt, dict): return None, None, None
    gt = gt.get("gt_parse", gt) if "gt_parse" in gt else gt
    menu = gt.get("menu") or []
    if isinstance(menu, dict):
        menu = [menu]
    items = []
    for m in menu:
        if not isinstance(m, dict): continue
        p = parse_money(m.get("price"))
        if p is not None: items.append(p)
    total_info = gt.get("total") or {}
    total_price = parse_money(total_info.get("total_price")) if isinstance(total_info, dict) else None
    tax = parse_money(total_info.get("tax_price")) if isinstance(total_info, dict) else None
    return items, total_price, (tax if tax is not None else 0.0)


def main():
    if not B_OUT.exists():
        OUT.write_text(json.dumps({"available": False, "reason": "B output missing"}, indent=2))
        print("B's runs/B_donut_cord_on_cord.json not found"); return
    b = json.loads(B_OUT.read_text())
    b_pred = {}
    for r in b.get("results", []):
        b_pred[r["id"]] = (r.get("pred"), r.get("gold"), r.get("correct", False))

    ds = load_dataset("naver-clova-ix/cord-v2", split="test", trust_remote_code=True)
    print(f"CORD test n={len(ds)}")

    per_rate = {}
    for rate in NOISE_RATES:
        per_seed_stats = []
        for seed in SEEDS:
            rng = random.Random(seed)
            n_correct = 0
            n_accepted = 0
            n_correct_accepted = 0
            n_total = 0
            for ex_idx in range(len(ds)):
                items, total, tau = extract_cord_items(ds[ex_idx])
                if not items or total is None: continue
                pred, gold, correct_flag = b_pred.get(ex_idx, (None, None, False))
                if pred is None: continue
                noisy = inject_noise(items, rate, rng)
                T = i3_reachable(noisy, tau)
                in_T = any(abs(pred - t) <= 0.02 for t in T)
                n_total += 1
                if correct_flag: n_correct += 1
                if in_T:
                    n_accepted += 1
                    if correct_flag: n_correct_accepted += 1
            per_seed_stats.append({
                "n": n_total,
                "coverage": n_accepted / max(1, n_total),
                "precision": n_correct_accepted / max(1, n_accepted),
                "base_F1": n_correct / max(1, n_total),
            })
        cov = sum(s["coverage"] for s in per_seed_stats) / len(per_seed_stats)
        prec = sum(s["precision"] for s in per_seed_stats) / len(per_seed_stats)
        per_rate[f"rate={rate}"] = {
            "n": per_seed_stats[0]["n"],
            "coverage_mean": cov,
            "precision_mean": prec,
            "per_seed": per_seed_stats,
        }

    summary = {
        "corpus": "CORD-v2 test (with synthetic money-line noise)",
        "noise_rates": NOISE_RATES,
        "seeds": SEEDS,
        "per_rate": per_rate,
        "note": (
            "Reports sigma's precision/coverage degradation as a function of synthetic noise applied "
            "to CORD's labeled item amounts. Models real-world OCR error (digit swap, decimal shift, "
            "item drop, spurious addition). At rate=0 we recover B's clean numbers. Graceful degradation "
            "= sigma remains useful at moderate noise. Sharp drop = sigma is fragile to label quality."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
