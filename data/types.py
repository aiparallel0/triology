"""Receipt + MoneyLine dataclasses.

Shape inferred from how `core/identities.py`, `core/money_lines.py`, and
the scripts under `scripts/` consume receipts. The Receipt API is
keyword-driven: the verifier asks "do you have a 'subtotal' line?" and
"what cents value is on it?", and the synthetic / SROIE / CORD loaders
each construct the same shape.

A receipt's `tau_cents()` is the *signed* offset that I2/I3 add to the
subset-sum of items. Following Paper 1's convention:

    tau = sum(tax_lines) + sum(service_lines) - sum(discount_lines)

Items are the money lines that are *not* tagged as one of
{subtotal, total, cash, change, tax, service, discount}. This is what
`items_cents()` returns.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


_NON_ITEM_TAGS = frozenset({
    "subtotal", "total", "cash", "change", "tax", "service", "discount",
})


@dataclass
class MoneyLine:
    line_idx: int
    value_cents: int
    raw_text: str
    tags: List[str] = field(default_factory=list)


@dataclass
class Receipt:
    receipt_id: str
    money_lines: List[MoneyLine]
    gold_total_cents: int
    # Optional: full text strings for S3's character-confusion alignment.
    gold_text: Optional[str] = None
    ocr_text: Optional[str] = None
    # Optional: free-form metadata loaders may attach (image path, etc.)
    meta: dict = field(default_factory=dict)

    def has_keyword(self, keyword: str) -> bool:
        return any(keyword in m.tags for m in self.money_lines)

    def keyword_lines(self, keyword: str) -> List[MoneyLine]:
        return [m for m in self.money_lines if keyword in m.tags]

    def items_cents(self) -> List[int]:
        """Money lines that aren't subtotal/total/cash/change/tax/etc."""
        return [
            m.value_cents for m in self.money_lines
            if not (set(m.tags) & _NON_ITEM_TAGS)
        ]

    def tau_cents(self) -> int:
        """Signed tax/service/discount offset added to item sum."""
        tau = 0
        for m in self.money_lines:
            if "tax" in m.tags or "service" in m.tags:
                tau += m.value_cents
            elif "discount" in m.tags:
                tau -= m.value_cents
        return tau
