"""Extract monetary values from raw OCR text lines.

A "money line" is any OCR line whose text contains at least one numeric
value matching a money pattern. We use a deliberately conservative regex:

    optional currency prefix   ($ / £ / RM / MYR / etc.)
    digits with optional thousands separators
    a decimal point
    exactly two decimal digits

Matches like "0.06" (a tax rate) and "100" (an integer with no decimal)
are intentionally rejected: tax rates aren't monetary values, and
receipt money values almost always have two decimal places. Real corpora
(SROIE Task-3, CORD-v2) follow this convention universally.

Returns the integer cent value to keep all downstream arithmetic in
exact integers. "RM 36.23" -> 3623; "$1,250.00" -> 125000.

The tagger (keyword_tagger.tag_line) runs over the same line text and
attaches semantic tags ("cash", "subtotal", etc.). This module is
purely about value extraction; we do not interpret what the line means.
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple

from .keyword_tagger import tag_line
from ..data.types import MoneyLine

# Money pattern: optional non-digit prefix, then digits-with-commas,
# decimal point, two decimal digits. Captured group 1 is the numeric
# string; we strip commas and convert.
_MONEY_RE = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})(?!\d)"
)


def parse_money_string(s: str) -> Optional[int]:
    """Parse '36.23' or '1,250.00' to integer cents. None on failure."""
    m = _MONEY_RE.search(s)
    if m is None:
        return None
    whole = m.group(1).replace(",", "")
    cents = m.group(2)
    try:
        return int(whole) * 100 + int(cents)
    except ValueError:
        return None


def extract_money_lines(raw_lines: List[str]) -> List[MoneyLine]:
    """Return one MoneyLine per OCR line that contains at least one value.

    If a line has multiple money values (e.g., "ITEM 2 @ 5.00 = 10.00"),
    only the LAST value is kept — the convention matches Paper 1's money-
    line extractor and aligns with how SROIE/CORD lay out unit-price-
    times-quantity-equals-line-total. This loses some information but
    avoids double-counting items in the subset-sum.
    """
    out: List[MoneyLine] = []
    for idx, line in enumerate(raw_lines):
        # Find ALL matches and take the rightmost (line-total convention).
        matches = list(_MONEY_RE.finditer(line))
        if not matches:
            continue
        m = matches[-1]
        whole = m.group(1).replace(",", "")
        cents = int(m.group(2))
        try:
            value_cents = int(whole) * 100 + cents
        except ValueError:
            continue
        out.append(MoneyLine(
            line_idx=idx,
            value_cents=value_cents,
            raw_text=line,
            tags=tag_line(line),
        ))
    return out


def find_total_candidate(money_lines: List[MoneyLine]) -> Optional[MoneyLine]:
    """Heuristic: the money line tagged 'total' (and not also 'subtotal').

    Used by loaders that need to identify the gold total when the corpus
    metadata leaves it implicit. Real loaders should prefer the corpus's
    own ground-truth total field; this is a fallback.
    """
    candidates = [
        m for m in money_lines
        if "total" in m.tags and "subtotal" not in m.tags
    ]
    if not candidates:
        return None
    # Prefer the LAST total-tagged line (receipts conventionally place
    # the grand total below subtotal/tax).
    return candidates[-1]
