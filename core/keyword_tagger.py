"""Keyword tagger for receipt money lines.

Lexicons are taken verbatim from Paper 1's "Tagger characterisation"
paragraph (Section VI). Substring match, case-insensitive, after
whitespace normalization. This is the same tagger that produced
Table II (cross-corpus availability):

    I1 (cash − change) :  38.3% SROIE / 0.0% CORD
    I2 (subtotal + τ) :  62.7% SROIE / 12.4% CORD
    I3 (subset-sum)    : 100.0% SROIE / 87.6% CORD

A more permissive tagger (fuzzy substring with edit distance 1) would
shift I1/I2 numbers up; a stricter one (exact-match-only) would shift
them down. We sit near the strict end intentionally so the reported
gap to I3 is an upper bound on what permissive tagging could narrow.

The tagger does NOT handle multi-line keywords (e.g., "SUB" on one
line and "TOTAL" on the next), nor does it disambiguate when a single
line carries two keywords (e.g., "TOTAL CASH"). Both of these are
out-of-scope: SROIE/CORD-v2 do not have the second pattern, and the
first is a layout-recovery problem the upstream tagger solves before
this module runs.
"""
from __future__ import annotations
import re
from typing import List, Optional, Tuple

# Lexicons, verbatim from Paper 1 §VI "Tagger characterisation".
LEX_CASH = (
    "cash", "tunai", "paid by cash",
)
LEX_CHANGE = (
    "change", "baki",
)
LEX_SUBTOTAL = (
    "subtotal", "sub-total", "sub total", "sub.total", "sub_total",
)
# Tax-adjustment lexicon. Paper 1 collapses tax/service/discount into a
# single "tau" offset at the verifier level but we keep the tags
# separated here so I4 (tax-rate consistency) can find tax-only lines.
LEX_TAX = (
    "tax", "gst", "sst",
)
LEX_SERVICE = (
    "service charge", "service",
)
LEX_DISCOUNT = (
    "discount",
)
LEX_TOTAL = (
    "total",  # caution: also matches "subtotal", so order matters
)

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text.strip().lower())


def tag_line(text: str) -> List[str]:
    """Return all matching tags for a single OCR line.

    The order of checks matters: subtotal/service must be checked before
    total/tax to prevent the prefix collisions ("subtotal" containing
    "total", "service" containing nothing-relevant).
    """
    norm = _normalize(text)
    tags = []
    if any(k in norm for k in LEX_SUBTOTAL):
        tags.append("subtotal")
    elif any(k in norm for k in LEX_TOTAL):
        tags.append("total")
    if any(k in norm for k in LEX_CASH):
        tags.append("cash")
    if any(k in norm for k in LEX_CHANGE):
        tags.append("change")
    if any(k in norm for k in LEX_SERVICE):
        tags.append("service")
    elif any(k in norm for k in LEX_TAX):
        tags.append("tax")
    if any(k in norm for k in LEX_DISCOUNT):
        tags.append("discount")
    return tags


def tag_lines(raw_lines: List[str]) -> List[List[str]]:
    """Tag every OCR line; returns parallel list of tag-lists."""
    return [tag_line(ln) for ln in raw_lines]
