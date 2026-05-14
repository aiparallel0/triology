"""sigma_reliability: calibration diagram for sigma on CORD.

Reviewer attack defended: 'is sigma well-calibrated? does its acceptance signal
track with intuitive notions of confidence?'

For CORD's sigma-accepted receipts (from B), bin by T_size and report
sigma_precision per bin. If sigma is well-calibrated, smaller T_size (cleaner
witness set) should yield higher precision.

Read-only CPU script on B's output. ~1 sec.
"""
import json
from collections import defaultdict
from pathlib import Path

B_OUT = Path("runs/B_donut_cord_on_cord.json")
OUT = Path("runs/sigma_reliability_cord.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

BINS = [(1, 1), (2, 4), (5, 9), (10, 49), (50, 199), (200, 9999)]


def bin_of(t_size):
    for lo, hi in BINS:
        if lo <= t_size <= hi:
            return f"{lo}-{hi}"
    return "unbinned"


def main():
    if not B_OUT.exists():
        OUT.write_text(json.dumps({"available": False, "reason": "B output missing"}, indent=2))
        print("B's runs/B_donut_cord_on_cord.json not found"); return
    b = json.loads(B_OUT.read_text())
    results = b.get("results", [])

    accepts = [r for r in results if r.get("in_T")]
    bins = defaultdict(list)
    for r in accepts:
        bins[bin_of(r.get("T_size", 0))].append(r)

    by_bin = {}
    for b_name, items in bins.items():
        n = len(items)
        correct = sum(r.get("correct", False) for r in items)
        by_bin[b_name] = {
            "n_accepted": n,
            "n_correct": correct,
            "precision": correct / max(1, n),
            "T_size_range": b_name,
        }

    # Overall accept stats for reference
    n_accepts = len(accepts)
    n_correct_all = sum(r.get("correct", False) for r in accepts)

    summary = {
        "corpus": "CORD-v2 test",
        "source": str(B_OUT),
        "n_accepts_total": n_accepts,
        "n_correct_total": n_correct_all,
        "overall_sigma_precision": n_correct_all / max(1, n_accepts),
        "by_T_size_bin": dict(sorted(by_bin.items(), key=lambda kv: int(kv[0].split('-')[0]))),
        "interpretation": (
            "If sigma is well-calibrated, smaller T_size (cleaner witness) yields higher precision. "
            "Monotone decrease of precision with T_size_bin suggests T_size could be used as an "
            "intra-sigma ranking signal for further refinement. Flat profile suggests sigma's accept "
            "is binary and not graded by T_size."
        ),
    }
    OUT.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
