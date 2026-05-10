"""AAD decoder: T-aware token mask and masked-softmax wrapper.

The math here matches §III of the Paper 3 draft (section3_aad.tex):

    M_t = { sigma in Sigma : prefix-val(y_<t · sigma) ∩ T != empty }
    p_AAD_t(sigma) = p_t(sigma) / sum_{s in M_t} p_t(s)   if sigma in M_t
                                                    0    otherwise

The implementation is in pure Python and is meant to instrument a black-
box decoder rather than replace one. It is used by:

  S5 (paper3.scripts.s5_aad_overhead) — micro-benchmark of mask compute
       cost per token.

  S7 (paper3.scripts.s7_aad_train_grid) — wraps any registered KIE
       model's decoder. The integration seam is build_mask(prefix_str,
       T) — the adapter's decoder calls this at every step.

We support the digits-and-decimal vocabulary

    Sigma = { '0','1',...,'9', '.', EOS }

Larger vocabularies (e.g., currency tokens) work too — the only
constraint is that prefix_to_value(prefix_str) returns a numeric value
or None for "not yet a complete number". Subclass _Tokenizer to plug in
a different vocabulary.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

from .subset_sum import EPS_CENTS

EOS = "<eos>"
DEFAULT_VOCAB: Tuple[str, ...] = tuple(list("0123456789.") + [EOS])


# ---------------------------------------------------------------------------
# Prefix → reachable values
# ---------------------------------------------------------------------------

def _digits_decimal_completions(prefix: str, T: Set[int],
                                eps_cents: int = EPS_CENTS,
                                max_extra_digits: int = 2) -> bool:
    """Can `prefix` be extended (within max_extra_digits) to a value in T?

    Strategy: parse `prefix` as a partial monetary string. If it is not a
    valid prefix of "DDD.DD" (or "DDD" before decimal), return False.
    Otherwise, enumerate candidate completions and check membership.

    For efficiency we enumerate only a few extra digits (max_extra_digits
    after the decimal). On the digits-and-decimal vocab this is enough
    because (a) the total field has fixed two-decimal format, and (b)
    monetary values in our corpora are bounded above by ~10000.00 RM.
    """
    # Check prefix is well-formed digits / one decimal point pattern
    if any(c not in "0123456789." for c in prefix):
        return False
    if prefix.count(".") > 1:
        return False

    if "." in prefix:
        whole, frac = prefix.split(".")
        # Once the decimal separator is committed, no more whole digits.
        max_whole_extra = 0
    else:
        whole, frac = prefix, ""
        max_whole_extra = 8 - len(whole)

    if len(frac) > 2:
        return False  # already over the 2-decimal budget
    if not whole and not frac:
        # empty prefix — anything is reachable iff T is nonempty
        return len(T) > 0

    # Parse current minimum / maximum value the prefix can grow into.
    # Rather than enumerate, we use range arithmetic: with up to k
    # remaining whole-digit slots and (2 - len(frac)) remaining frac
    # slots, the value range is [low, high].
    return _range_intersects_T(whole, frac, T, eps_cents,
                               max_whole_extra=max_whole_extra)


def _range_intersects_T(whole: str, frac: str, T: Set[int],
                        eps_cents: int, max_whole_extra: int) -> bool:
    """True iff some completion of (whole, frac) into a 2-decimal value
    lies within EPS_CENTS of any t in T."""
    # Reduce T to a sorted list for binary search.
    if not T:
        return False
    T_sorted = sorted(T)

    # Enumerate completions: for k in 0..max_whole_extra extra whole
    # digits, and for f in 0..(2-len(frac)) extra frac digits, compute
    # min/max possible value-in-cents and check if any T point intersects.
    frac_extra_choices = range(0, 3 - len(frac))
    whole_extra_choices = range(0, max_whole_extra + 1)
    for k in whole_extra_choices:
        for f in frac_extra_choices:
            full_whole_len = len(whole) + k
            full_frac_len = len(frac) + f
            if full_frac_len != 2:
                continue
            # Min value: pad whole with leading zeros wouldn't increase
            # but adding trailing zero-extra-whole digits multiplies by 10^k.
            # The lower bound of the value-range is achieved when extra
            # whole digits are all 0 (tightest at given prefix), upper
            # bound when all 9.
            lo_whole = int(whole) * (10 ** k) if whole else 0
            hi_whole = (int(whole) + 1) * (10 ** k) - 1 if whole else (10 ** k - 1)
            lo_frac = int(frac.ljust(2, "0")) if frac else 0
            hi_frac = int((frac + "9" * f).ljust(2, "0")) if frac or f else 99
            lo = lo_whole * 100 + lo_frac
            hi = hi_whole * 100 + hi_frac
            # Does [lo - eps, hi + eps] intersect T?
            import bisect
            i = bisect.bisect_left(T_sorted, lo - eps_cents)
            if i < len(T_sorted) and T_sorted[i] <= hi + eps_cents:
                return True
    return False


# ---------------------------------------------------------------------------
# Mask construction
# ---------------------------------------------------------------------------

def build_mask(prefix: str, T: Set[int],
               vocab: Iterable[str] = DEFAULT_VOCAB,
               eps_cents: int = EPS_CENTS) -> FrozenSet[str]:
    """Return the T-feasible token set M_t at decoding step t.

    Args:
        prefix : the decoded-so-far string (digits and at most one '.')
        T      : reachability set in cents
        vocab  : the decoding vocabulary

    Returns:
        FrozenSet of vocab symbols whose prefix has at least one
        completion ending in some w in T.

    Special handling:
        EOS is in the mask iff the current `prefix`, parsed as a
        complete value, lies within EPS of some t in T.
    """
    feasible = set()
    for sigma in vocab:
        if sigma == EOS:
            # Accept EOS iff prefix is a complete value within T
            try:
                if "." in prefix:
                    whole, frac = prefix.split(".")
                    if len(frac) != 2 or not whole:
                        continue
                    val = int(whole) * 100 + int(frac)
                else:
                    if not prefix:
                        continue
                    val = int(prefix) * 100
                if any(abs(val - t) <= eps_cents for t in T):
                    feasible.add(EOS)
            except (ValueError, IndexError):
                continue
        else:
            new_prefix = prefix + sigma
            if _digits_decimal_completions(new_prefix, T, eps_cents):
                feasible.add(sigma)
    return frozenset(feasible)


# ---------------------------------------------------------------------------
# AAD-distribution wrapper around an unconstrained next-token softmax
# ---------------------------------------------------------------------------

@dataclass
class AADStep:
    """Result of one AAD decoding step."""
    mask: FrozenSet[str]
    p_aad: Dict[str, float]
    abstained: bool  # True iff M_t was empty and we fell through to p_t


def aad_step(prefix: str, T: Set[int], p_t: Dict[str, float],
             vocab: Iterable[str] = DEFAULT_VOCAB,
             eps_cents: int = EPS_CENTS) -> AADStep:
    """One AAD decoding step.

    Args:
        prefix : decoded-so-far string
        T      : reachability set
        p_t    : unconstrained next-token distribution (keys must cover vocab)
        vocab  : decoding vocab

    Returns:
        AADStep with the mask, the renormalized distribution, and an
        abstention flag (Choice 2 in §III.E: empty M_t -> fall through
        to p_t rather than backtrack).
    """
    M = build_mask(prefix, T, vocab, eps_cents)
    if not M:
        # Abstain: pass through unconstrained distribution
        return AADStep(mask=frozenset(), p_aad=dict(p_t), abstained=True)
    Z = sum(p_t.get(sigma, 0.0) for sigma in M)
    if Z <= 0.0:
        # All mass on infeasible tokens — also abstain
        return AADStep(mask=M, p_aad=dict(p_t), abstained=True)
    p_aad = {sigma: (p_t.get(sigma, 0.0) / Z if sigma in M else 0.0)
             for sigma in vocab}
    return AADStep(mask=M, p_aad=p_aad, abstained=False)


def gold_probability(gold_text: str, T: Set[int],
                     decoder_p_fn,  # callable: (prefix) -> dict
                     vocab: Iterable[str] = DEFAULT_VOCAB,
                     eps_cents: int = EPS_CENTS,
                     constrained: bool = True) -> float:
    """Compute P(gold_text | constrained) for a black-box decoder.

    decoder_p_fn(prefix) must return the unconstrained next-token
    distribution at that prefix. Used by S6 (expectation simulation)
    and as a sanity check for the regret bound (Theorem 1).
    """
    p = 1.0
    for i, c in enumerate(gold_text + EOS):
        prefix = gold_text[:i]
        p_t = decoder_p_fn(prefix)
        if constrained:
            step = aad_step(prefix, T, p_t, vocab, eps_cents)
            p *= step.p_aad.get(c, 0.0)
        else:
            p *= p_t.get(c, 0.0)
        if p == 0.0:
            return 0.0
    return p
