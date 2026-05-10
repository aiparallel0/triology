"""Subset-sum reachability set T(r).

Lifted unchanged from Paper 1's reproducibility code except for:
  - explicit type annotations
  - exposing the witness-count k via the returned mapping (was discarded)
  - a separate reachable_targets_with_offset() that takes tau as an explicit
    argument rather than baked into the items list

The DP itself is the classical sparse 0/1 subset-sum: best[s] = minimum
number of items summing to s. Time O(n * v_max) in cents, space O(|S| * n)
where |S| is the number of distinct partial sums encountered. On SROIE
Task-3 this runs at 0.48 ms mean / 3.26 ms p95 (Paper 1 Table I).

EPS_CENTS = 2 is the same tolerance Paper 1 uses to allow for rounding
ambiguity (one-cent rounding on a tax subtotal, etc.). It is small enough
not to admit sibling-line confusion in practice.
"""
from __future__ import annotations
from typing import Dict, List, Set, Tuple

EPS_CENTS = 2  # tolerance, matches Paper 1


def reachable_targets(items_cents: List[int], tau_cents: int,
                      k_min: int = 1) -> Set[int]:
    """Return {sum(S) + tau : S subset of items, |S| >= k_min}.

    Convention from Paper 1: when tau != 0 the subset can be empty (k_min=1
    means "at least one item OR a non-zero tax line") — but we lift k_min
    to 2 when tau == 0 to forbid the degenerate "single-item-equals-total"
    acceptance.

    >>> sorted(reachable_targets([350, 1200], 93, k_min=1))
    [443, 1293, 1643]
    """
    best: Dict[int, int] = {0: 0}  # sum -> min witness count
    for v in items_cents:
        snap = list(best.items())
        for s, k in snap:
            ns, nk = s + v, k + 1
            if ns not in best or best[ns] > nk:
                best[ns] = nk
    return {s + tau_cents for s, k in best.items() if k >= k_min}


def reachable_targets_with_witness(items_cents: List[int], tau_cents: int,
                                   k_min: int = 1) -> Dict[int, int]:
    """Same as reachable_targets but returns sum -> min witness count map.

    Useful for downstream analyses (e.g., "what is |T| restricted to subsets
    of size >= 2?", or "how does |T| grow with witness count?").
    """
    best: Dict[int, int] = {0: 0}
    for v in items_cents:
        snap = list(best.items())
        for s, k in snap:
            ns, nk = s + v, k + 1
            if ns not in best or best[ns] > nk:
                best[ns] = nk
    return {s + tau_cents: k for s, k in best.items() if k >= k_min}


def i3_accepts(candidate_cents: int, items_cents: List[int],
               tau_cents: int, eps_cents: int = EPS_CENTS) -> bool:
    """Paper 1's I_3 verifier: does candidate fall within EPS of any T value?

    Auto-selects k_min: requires |S| >= 2 when tau == 0 (forbids the
    "candidate equals a single item line" trivial acceptance), |S| >= 1
    otherwise (tax line alone may sum with empty item set in pathological
    cases — extremely rare).
    """
    k_min = 1 if tau_cents != 0 else 2
    targets = reachable_targets(items_cents, tau_cents, k_min)
    return any(abs(candidate_cents - t) <= eps_cents for t in targets)


def t_size(items_cents: List[int], tau_cents: int, k_min: int = 1) -> int:
    """|T(r)| — the cardinality of the reachability set."""
    return len(reachable_targets(items_cents, tau_cents, k_min))
