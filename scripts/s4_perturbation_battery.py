"""S4 — Perturbation battery / T-shift table.

Fills `tab:t_shift` in §II and the T-shift row in §VI.

Compares verifier (I3) false-acceptance under four perturbation models:

  random            : uniform replacement in [gold/2, gold*3/2]   (Paper 1 baseline)
  single-digit-uniform : Paper 1's E3-style uniform single-digit  (Paper 1 9.44%)
  two-digit-swap    : Paper 1's two-digit swap                    (Paper 1 1.63%)
  empirical         : sample wrong digits from the confusion matrix
                      output by S3 (P(ocr-digit | gold-digit))

The empirical column closes Paper 1's Threat T1 by replacing synthetic
single-digit corruption with an empirically-supported model. Reading
order across columns IS the T-shift: the verifier's response under
"realistic" perturbations relative to the worst-case-uniform synthetic
characterisation Paper 1 reports.

Usage:
    python -m paper3.scripts.s4_perturbation_battery \\
        --corpus synthetic --n 2000 \\
        --confusion_json results/s3_cord_confusion.json
"""
from __future__ import annotations
import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..data import load_corpus
from ..core.subset_sum import i3_accepts, EPS_CENTS
from ..core.stats import wilson_ci, fmt_proportion

RESULTS = Path("results")


# ---------------------------------------------------------------------------
# Perturbation models — modify a gold value into a wrong candidate
# ---------------------------------------------------------------------------

def perturb_random(gold: int, rng: random.Random,
                   confusion_p: Optional[np.ndarray] = None) -> int:
    lo = max(1, gold // 2)
    hi = max(lo + 1, gold * 3 // 2)
    return rng.randint(lo, hi)


def perturb_single_digit_uniform(gold: int, rng: random.Random,
                                 confusion_p: Optional[np.ndarray] = None) -> int:
    s = str(gold)
    for _ in range(10):
        pos = rng.randint(0, len(s) - 1)
        old = s[pos]
        new = rng.choice([d for d in "0123456789" if d != old])
        if pos == 0 and new == "0" and len(s) > 1:
            continue
        return int(s[:pos] + new + s[pos+1:])
    return gold


def perturb_two_digit_swap(gold: int, rng: random.Random,
                           confusion_p: Optional[np.ndarray] = None) -> int:
    s = list(str(gold))
    if len(s) < 2: return gold
    for _ in range(10):
        pos = rng.randint(0, len(s) - 2)
        if s[pos] == s[pos+1]: continue
        s2 = s[:]; s2[pos], s2[pos+1] = s2[pos+1], s2[pos]
        if s2[0] == "0" and len(s2) > 1: continue
        return int("".join(s2))
    return gold


def perturb_empirical(gold: int, rng: random.Random,
                      confusion_p: Optional[np.ndarray] = None) -> int:
    """Sample one wrong digit from the empirical P(ocr | gold) distribution.

    If confusion_p is None or has zero off-diagonal mass, falls back
    to single_digit_uniform so the script still runs without S3 output.
    """
    if confusion_p is None:
        return perturb_single_digit_uniform(gold, rng)
    s = str(gold)
    digits_in_gold = [(i, c) for i, c in enumerate(s) if c.isdigit()]
    if not digits_in_gold:
        return gold
    # Pick a position weighted by how confusable that digit is
    weights = []
    for _, c in digits_in_gold:
        g = int(c)
        # Off-diagonal mass for digit g
        row = confusion_p[g].copy()
        row[g] = 0.0
        weights.append(row.sum())
    total_w = sum(weights)
    if total_w <= 0:
        return perturb_single_digit_uniform(gold, rng)
    weights = [w / total_w for w in weights]
    pos_idx = rng.choices(range(len(digits_in_gold)), weights=weights, k=1)[0]
    pos, c = digits_in_gold[pos_idx]
    g = int(c)
    row = confusion_p[g].copy()
    row[g] = 0.0
    if row.sum() <= 0:
        return perturb_single_digit_uniform(gold, rng)
    new_digit = rng.choices(range(10), weights=row.tolist(), k=1)[0]
    new = str(new_digit)
    if pos == 0 and new == "0" and len(s) > 1:
        return perturb_single_digit_uniform(gold, rng)
    return int(s[:pos] + new + s[pos+1:])


PERTURBATIONS = {
    "random":               perturb_random,
    "single_digit_uniform": perturb_single_digit_uniform,
    "two_digit_swap":       perturb_two_digit_swap,
    "empirical":            perturb_empirical,
}


# ---------------------------------------------------------------------------
# Battery
# ---------------------------------------------------------------------------

def run_battery(receipts, confusion_p: Optional[np.ndarray],
                seed: int = 0, retries: int = 8) -> Dict:
    """For each receipt and each perturbation, measure I3 false-acceptance.

    Returns per-perturbation rate + Wilson CI.
    """
    rng = random.Random(seed)
    receipts = list(receipts)
    out = {"n": len(receipts), "by_perturbation": {}}
    for name, fn in PERTURBATIONS.items():
        accepted = 0
        eligible = 0
        for r in receipts:
            items = r.items_cents()
            tau = r.tau_cents()
            if not items:
                continue
            gold = r.gold_total_cents
            # Try several perturbations to land on a non-gold value
            w = gold
            for _ in range(retries):
                w = fn(gold, rng, confusion_p)
                if w != gold:
                    break
            if w == gold:
                continue
            eligible += 1
            if i3_accepts(w, items, tau):
                accepted += 1
        rate = accepted / eligible if eligible else 0.0
        lo, hi = wilson_ci(accepted, eligible)
        out["by_perturbation"][name] = {
            "eligible": eligible,
            "accepted": accepted,
            "false_acceptance_rate": rate,
            "ci_low": lo,
            "ci_high": hi,
            "fmt": fmt_proportion(accepted, eligible),
        }
    return out


def render_t_shift_table(stats: Dict) -> str:
    rows = stats["by_perturbation"]
    lines = []
    lines.append("T-shift table: I3 false-acceptance under perturbation models")
    lines.append("=" * 72)
    lines.append(f"{'Perturbation':<24}  {'False-acceptance (Wilson 95% CI)':<35}")
    lines.append("-" * 72)
    order = ["random", "single_digit_uniform", "two_digit_swap", "empirical"]
    for name in order:
        if name not in rows:
            continue
        r = rows[name]
        lines.append(f"{name:<24}  {r['fmt']:<35}")
    lines.append("")
    lines.append("Paper 1 reference (Table I, n=2000 synthetic, 5 seeds):")
    lines.append("  random               :  5.86 ± 0.68%")
    lines.append("  single-digit OCR     :  9.44 ± 0.10%")
    lines.append("  two-digit swap       :  1.63 ± 0.29%")
    lines.append("  empirical (CORD-v2)  :  Paper 3 (this row)")
    return "\n".join(lines)


def parse_args():
    ap = argparse.ArgumentParser(description="S4: perturbation battery / T-shift")
    ap.add_argument("--corpus", choices=["sroie", "synthetic"],
                    default="synthetic")
    ap.add_argument("--path", default=None)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--confusion_json",
                    default="results/s3_cord_confusion.json",
                    help="path to S3 output; falls back to single-digit uniform "
                         "if missing or empty")
    ap.add_argument("--out_json", default="results/s4_perturbation_battery.json")
    ap.add_argument("--out_txt",  default="results/s4_perturbation_battery.txt")
    return ap.parse_args()


def load_confusion(path: str) -> Optional[np.ndarray]:
    p = Path(path)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError:
        return None
    arr = d.get("P_ocr_given_gold")
    if arr is None:
        return None
    a = np.array(arr, dtype=np.float64)
    if a.shape != (10, 10):
        return None
    return a


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)
    confusion_p = load_confusion(args.confusion_json)
    if confusion_p is not None:
        print(f"[s4] loaded confusion matrix from {args.confusion_json}",
              file=sys.stderr)
    else:
        print(f"[s4] no confusion matrix at {args.confusion_json}; "
              f"empirical column will fall back to uniform",
              file=sys.stderr)

    recs = load_corpus(args.corpus, path=args.path, n=args.n,
                       seed=args.seed, max_receipts=args.max)
    stats = run_battery(recs, confusion_p, seed=args.seed)
    Path(args.out_json).write_text(json.dumps(stats, indent=2))
    table = render_t_shift_table(stats)
    Path(args.out_txt).write_text(table)
    print(table)
    print(f"\n[s4] wrote {args.out_json}, {args.out_txt}", file=sys.stderr)


if __name__ == "__main__":
    main()
