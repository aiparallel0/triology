"""Identities I1 through I5 — availability and acceptance.

Paper 1 introduces I1 (cash − change), I2 (subtotal + τ), and I3 (subset-
sum). The journal extension adds:

  I4 — tax-rate consistency at rate r (default 0.06, Malaysia GST)
       requires both a subtotal-tagged and a tax-tagged line, and asks
       whether |tax - subtotal * r| <= EPS_CENTS.

  I5 — per-item digit-validity (D3, currently parameterizable; default
       below). The role of I5 is to catch totals whose digit string
       contains characters not present anywhere in the receipt's money
       lines (a strong indicator of upstream OCR hallucination).

Each identity has TWO functions:

  available(receipt) -> bool
       Can this identity fire on this receipt at all? (Lexical or
       structural prerequisite met.) Used to compute Table II / Table IV
       availability rates.

  accepts(receipt, candidate_cents) -> bool
       Given that the identity is available, does it accept candidate as
       a plausible total? Used to compute false-acceptance and
       sibling-line rejection rates.

Availability without acceptance is the verifier-coverage figure of merit
(Paper 1's core claim). Acceptance given availability is the error-mode
characterisation (Paper 1 Tables I, III).
"""
from __future__ import annotations
from typing import Callable, Optional

from ..data.types import Receipt
from .subset_sum import EPS_CENTS, i3_accepts


# ---------------------------------------------------------------------------
# I1 — cash − change = total
# ---------------------------------------------------------------------------

def i1_available(r: Receipt) -> bool:
    return r.has_keyword("cash") and r.has_keyword("change")


def i1_accepts(r: Receipt, candidate_cents: int) -> bool:
    if not i1_available(r):
        return False
    cash_lines = r.keyword_lines("cash")
    change_lines = r.keyword_lines("change")
    # Take the largest cash and change values when multiples appear
    # (rare but possible — e.g., "CASH USD" + "CASH MYR").
    cash = max(m.value_cents for m in cash_lines)
    change = max(m.value_cents for m in change_lines)
    return abs((cash - change) - candidate_cents) <= EPS_CENTS


# ---------------------------------------------------------------------------
# I2 — subtotal + τ = total
# ---------------------------------------------------------------------------

def i2_available(r: Receipt) -> bool:
    return r.has_keyword("subtotal")


def i2_accepts(r: Receipt, candidate_cents: int) -> bool:
    if not i2_available(r):
        return False
    subtotal_lines = r.keyword_lines("subtotal")
    subtotal = max(m.value_cents for m in subtotal_lines)
    return abs(subtotal + r.tau_cents() - candidate_cents) <= EPS_CENTS


# ---------------------------------------------------------------------------
# I3 — structural subset-sum (Paper 1 headline identity)
# ---------------------------------------------------------------------------

def i3_available(r: Receipt) -> bool:
    """I3 needs at least 2 item lines (or 1 item + a non-zero tau)."""
    items = r.items_cents()
    tau = r.tau_cents()
    if tau != 0:
        return len(items) >= 1
    return len(items) >= 2


def i3_accepts_receipt(r: Receipt, candidate_cents: int) -> bool:
    if not i3_available(r):
        return False
    return i3_accepts(candidate_cents, r.items_cents(), r.tau_cents())


# ---------------------------------------------------------------------------
# I4 — tax-rate consistency at rate r (default 0.06, Malaysia GST)
# ---------------------------------------------------------------------------

DEFAULT_TAX_RATE = 0.06  # Locked in dashboards (D2)
TAX_RATE_TOLERANCE_CENTS = 2  # one-cent rounding either side


def i4_available(r: Receipt, rate: float = DEFAULT_TAX_RATE,
                 tol_cents: int = TAX_RATE_TOLERANCE_CENTS) -> bool:
    """I4 needs:
        (a) a subtotal-tagged line AND a tax-tagged line, AND
        (b) tax-line ≈ subtotal × rate

    Per D2 (locked: rate=0.06, Malaysia GST), receipts whose tax rate
    is not 6% fail (b) and I4 simply does not fire — they fall back to
    I1, I2, I3, I5. This matches the dashboard wording: "Receipts where
    the tax rate is not 6% will simply not have I₄ fire."

    The structural-prerequisite (b) is what differentiates I4 from a
    weakened I2: I2 just adds tax to subtotal; I4 additionally
    *constrains* what the tax line is allowed to be.
    """
    if not (r.has_keyword("subtotal") and r.has_keyword("tax")):
        return False
    subtotal = max(m.value_cents for m in r.keyword_lines("subtotal"))
    tax_total = sum(m.value_cents for m in r.keyword_lines("tax"))
    expected_tax_cents = round(subtotal * rate)
    return abs(tax_total - expected_tax_cents) <= tol_cents


def i4_accepts(r: Receipt, candidate_cents: int,
               rate: float = DEFAULT_TAX_RATE,
               tol_cents: int = TAX_RATE_TOLERANCE_CENTS) -> bool:
    """Once available, accept iff candidate ≈ subtotal + tax-line."""
    if not i4_available(r, rate, tol_cents):
        return False
    subtotal = max(m.value_cents for m in r.keyword_lines("subtotal"))
    tax_total = sum(m.value_cents for m in r.keyword_lines("tax"))
    return abs(subtotal + tax_total - candidate_cents) <= EPS_CENTS


# ---------------------------------------------------------------------------
# I5 — per-item digit-validity (D3 still pending — pluggable rule)
# ---------------------------------------------------------------------------

# Default I5 rule: every digit character in the candidate's decimal string
# must appear at least once across the union of all money-line digit
# strings. This is the weakest non-trivial digit-validity rule and is
# easy to satisfy on most real receipts (digits 0-9 nearly always all
# appear once a receipt has more than ~5 lines). The IJDAR submission
# may pick a stronger rule; we expose the rule as a callable so it can
# be swapped without changing the rest of the harness.

I5Rule = Callable[[Receipt, int], bool]


def i5_rule_digit_pool(r: Receipt, candidate_cents: int) -> bool:
    """Default I5: every digit in candidate appears in the money-line pool.

    candidate '3623' in cents (i.e., 36.23) needs digits {3, 6, 2} to
    each appear somewhere in the money lines. A strict reading would
    use position-aligned matching; this loose version is the default.
    """
    pool: set = set()
    for m in r.money_lines:
        # Use the line's value_cents formatted with the same convention
        # as the candidate (decimal string), not the raw OCR text.
        pool.update(str(m.value_cents))
    candidate_digits = set(str(candidate_cents))
    return candidate_digits.issubset(pool)


def i5_rule_position_aligned(r: Receipt, candidate_cents: int) -> bool:
    """Stronger I5: every digit position of candidate appears at the SAME
    position (counting from the decimal point) in some money line."""
    cand_str = str(candidate_cents).zfill(3)  # at least 3 digits (0.00)
    line_strs = [str(m.value_cents).zfill(3) for m in r.money_lines]
    # Right-align (decimal point at index -2). For each position from
    # the right, check that candidate's digit appears at that same
    # right-offset in some money line.
    for offset in range(len(cand_str)):
        c_digit = cand_str[-(offset + 1)]
        found = False
        for s in line_strs:
            if offset < len(s) and s[-(offset + 1)] == c_digit:
                found = True
                break
        if not found:
            return False
    return True


def i5_available(r: Receipt) -> bool:
    """I5 is available iff there is at least one money line (otherwise
    the digit pool is empty and the rule is degenerate)."""
    return len(r.money_lines) >= 1


def i5_accepts(r: Receipt, candidate_cents: int,
               rule: I5Rule = i5_rule_digit_pool) -> bool:
    if not i5_available(r):
        return False
    return rule(r, candidate_cents)


# ---------------------------------------------------------------------------
# Convenience: dispatch by identity name
# ---------------------------------------------------------------------------

IDENTITY_NAMES = ("I1", "I2", "I3", "I4", "I5")

_AVAIL_FNS = {
    "I1": i1_available, "I2": i2_available, "I3": i3_available,
    "I4": i4_available, "I5": i5_available,
}
_ACCEPT_FNS = {
    "I1": i1_accepts, "I2": i2_accepts, "I3": i3_accepts_receipt,
    "I4": i4_accepts, "I5": i5_accepts,
}


def is_available(identity: str, r: Receipt) -> bool:
    return _AVAIL_FNS[identity](r)


def is_accepted(identity: str, r: Receipt, candidate_cents: int) -> bool:
    return _ACCEPT_FNS[identity](r, candidate_cents)
