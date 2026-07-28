#!/usr/bin/env python3
"""R2-d: is the SROIE inversion consistent with OCR noise, or is that a story?

Reviewer 2: "the SROIE results (sigma underperforms softmax) are explained due
to OCR noise, but it is left as an untested hypothesis rather than empirically
verified."

The hypothesis: on OCR-derived corpora the multi-candidate extractor surfaces
extra monetary amounts, which inflates the reachable set T(M) and lets a WRONG
predicted total find a coincidental subset-sum witness. If true, sigma's FALSE
ACCEPTS on SROIE should sit on receipts with more extracted amounts / more
candidates / larger reachable sets than its TRUE ACCEPTS.

Pure stdlib, no GPU, no re-inference: reads the committed per-receipt records.
Permutation test on the difference of means, one-sided in the direction the
hypothesis predicts (false accepts have MORE of the thing).

A negative result is a real result. It would mean the OCR story is unsupported
and the paper must say so.

    python3 scripts/smoke/R2d_sroie_ocr_hypothesis.py
"""
import json
import os
import random
import sys

RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '..', '..', 'runs', 'A_donut_cord_on_sroie.json')
B = 20000
SEED = 12345
FIELDS = ['n_tau_candidates', 'money_count', 'T_size']


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def perm_p(a, b, reps=B, seed=SEED):
    """One-sided: P(mean(a) - mean(b) >= observed) under label exchange."""
    obs = mean(a) - mean(b)
    pool = list(a) + list(b)
    na = len(a)
    rng = random.Random(seed)
    hits = 0
    for _ in range(reps):
        rng.shuffle(pool)
        if mean(pool[:na]) - mean(pool[na:]) >= obs:
            hits += 1
    return obs, (hits + 1) / (reps + 1)


def main():
    d = json.load(open(RUN, encoding='utf8'))
    rec = d['results']
    acc = [r for r in rec if r.get('in_T')]
    if not acc:
        print("NO sigma-ACCEPTED RECEIPTS FOUND -- wrong run file? check did "
              "not run")
        return 2

    wrong = [r for r in acc if not r.get('correct')]
    right = [r for r in acc if r.get('correct')]

    print(f"SROIE, n={len(rec)}")
    print(f"  sigma accepts: {len(acc)}   correct: {len(right)}   "
          f"false accepts: {len(wrong)}   precision: "
          f"{len(right)/len(acc):.3f}")
    if len(wrong) < 5:
        print(f"  UNDERPOWERED: only {len(wrong)} false accepts. Any test here "
              f"is a consistency statement at best.")

    print()
    print("  Hypothesis: false accepts sit on receipts with MORE extracted")
    print("  amounts / candidates / reachable sums than true accepts.")
    print(f"  One-sided permutation test, B={B}.")
    print()
    print(f"  {'field':<20}{'false':>9}{'true':>9}{'diff':>9}{'p':>9}")
    any_sig = False
    for f in FIELDS:
        a = [r[f] for r in wrong if isinstance(r.get(f), (int, float))]
        b = [r[f] for r in right if isinstance(r.get(f), (int, float))]
        if not a or not b:
            print(f"  {f:<20}{'--':>9}{'--':>9}  (field absent)")
            continue
        diff, p = perm_p(a, b)
        star = ' *' if p < 0.05 else ''
        any_sig = any_sig or p < 0.05
        print(f"  {f:<20}{mean(a):>9.2f}{mean(b):>9.2f}{diff:>9.2f}{p:>9.4f}{star}")

    print()
    if any_sig:
        print("  READ: at least one measure supports the OCR-noise account.")
    else:
        print("  READ: NOT SUPPORTED at alpha=0.05. The OCR account remains a")
        print("  hypothesis, and the paper must keep saying so. Do not report")
        print("  a null as if it were a confirmation.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
