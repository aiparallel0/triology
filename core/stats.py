"""Wilson 95% binomial CI — matches the convention of Paper 1's Table II.

Wilson is preferred over normal-approximation when n is small or the
proportion is near 0/1 (both common for Paper 3's CORD-v2 cohort of
n=100 receipts). The score interval is asymmetric and stays inside
[0, 1] without ad-hoc clipping.

Also includes paired-bootstrap utilities, the standard non-parametric
CI for differences between paired predictions.
"""
from __future__ import annotations
import math
import random
from typing import List, Sequence, Tuple

# Standard normal 97.5th percentile, hard-coded to avoid scipy dep.
Z_975 = 1.959963984540054


def wilson_ci(successes: int, total: int, z: float = Z_975) -> Tuple[float, float]:
    """Wilson score interval for binomial proportion.

    Returns (lower, upper) in [0, 1]. If total == 0, returns (0.0, 1.0)
    by convention (no information).

    >>> low, hi = wilson_ci(347, 347)
    >>> round(low, 3), round(hi, 3)
    (0.989, 1.0)
    """
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    n = total
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


def fmt_proportion(successes: int, total: int, pct: bool = True) -> str:
    """Format like Paper 1's Table II: '38.3% [33.4, 43.5]'."""
    if total == 0:
        return "n/a"
    p = successes / total
    lo, hi = wilson_ci(successes, total)
    if pct:
        return f"{p*100:.1f}% [{lo*100:.1f}, {hi*100:.1f}]"
    return f"{p:.3f} [{lo:.3f}, {hi:.3f}]"


def paired_bootstrap_ci(values_a: Sequence[float], values_b: Sequence[float],
                        n_resamples: int = 1000, alpha: float = 0.05,
                        seed: int = 42) -> Tuple[float, float]:
    """Paired bootstrap CI on (mean_a - mean_b).

    Standard non-parametric CI used for delta-F1 confidence intervals
    on per-image correctness.
    """
    if len(values_a) != len(values_b):
        raise ValueError("paired bootstrap requires equal-length sequences")
    rng = random.Random(seed)
    n = len(values_a)
    deltas = []
    for _ in range(n_resamples):
        sample_idx = [rng.randint(0, n - 1) for _ in range(n)]
        a = sum(values_a[i] for i in sample_idx) / n
        b = sum(values_b[i] for i in sample_idx) / n
        deltas.append(a - b)
    deltas.sort()
    lo = deltas[int(alpha / 2 * n_resamples)]
    hi = deltas[int((1 - alpha / 2) * n_resamples)]
    return (lo, hi)


def percentile(values: Sequence[float], p: float) -> float:
    """Linear-interpolated percentile, p in [0, 100]."""
    if not values:
        return float("nan")
    s = sorted(values)
    idx = (p / 100) * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    frac = idx - lo
    return s[lo] * (1 - frac) + s[hi] * frac
