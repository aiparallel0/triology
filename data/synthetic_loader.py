"""Synthetic receipt generator — smoke-test fixture.

Produces `Receipt` objects whose structure satisfies the soundness
guarantees the smoke test asserts:

  * I3 (subset-sum) accepts the gold total 100% of the time when
    available — by construction, gold = sum(items) + tau.
  * I5 (digit-pool) accepts the gold total 100% of the time when
    available — every receipt includes a 'total' money line with the
    gold value, which makes the digit-pool a superset of gold's digits.

Profiles:
  default / sroie_like : items + subtotal + tax (6% sometimes) + total +
                         cash/change roughly half the time
  cord_like            : sparser keyword tagging — items + total only
                         ~70% of the time, matching CORD-v2's lower I1/I2
                         coverage in Paper 1's Table II.

For S3's character-confusion alignment, each receipt also carries
`gold_text` (a deterministic textual rendering) and `ocr_text` (the
gold rendering with each digit independently corrupted at probability
`confusion_rate` according to a fixed digit-confusion prior).
"""
from __future__ import annotations
import random
from typing import Dict, Iterator, List, Optional, Tuple

from .types import Receipt, MoneyLine

try:
    from ..core.keyword_tagger import tag_line
except (ImportError, ValueError):
    # Fallback if invoked outside the package.
    def tag_line(text: str) -> List[str]:
        return []


# A small fixed digit-confusion prior. Rows sum to 1.
# Diagonal is 1 - off_diag_mass; smoke test injects `confusion_rate`
# externally so we just describe relative weights for off-diagonal.
_OFF_DIAG_PRIOR: Dict[str, List[Tuple[str, float]]] = {
    "0": [("6", 0.4), ("8", 0.3), ("9", 0.3)],
    "1": [("7", 0.5), ("4", 0.3), ("l", 0.2)],
    "2": [("7", 0.5), ("8", 0.3), ("3", 0.2)],
    "3": [("8", 0.5), ("5", 0.3), ("9", 0.2)],
    "4": [("1", 0.4), ("9", 0.3), ("7", 0.3)],
    "5": [("3", 0.4), ("8", 0.3), ("6", 0.3)],
    "6": [("0", 0.4), ("8", 0.3), ("5", 0.3)],
    "7": [("1", 0.5), ("2", 0.3), ("4", 0.2)],
    "8": [("3", 0.4), ("0", 0.3), ("6", 0.3)],
    "9": [("4", 0.3), ("0", 0.3), ("3", 0.4)],
}
# Restrict to digit-only output so S3's digit-vs-digit alignment is
# well-defined (drop the "1 -> l" mapping).
for k in _OFF_DIAG_PRIOR:
    _OFF_DIAG_PRIOR[k] = [(d, w) for d, w in _OFF_DIAG_PRIOR[k] if d.isdigit()]
    s = sum(w for _, w in _OFF_DIAG_PRIOR[k])
    _OFF_DIAG_PRIOR[k] = [(d, w / s) for d, w in _OFF_DIAG_PRIOR[k]]


def _sample_corruption(digit: str, rng: random.Random) -> str:
    choices = _OFF_DIAG_PRIOR.get(digit)
    if not choices:
        return digit
    weights = [w for _, w in choices]
    chars = [c for c, _ in choices]
    return rng.choices(chars, weights=weights, k=1)[0]


def _corrupt_text(text: str, confusion_rate: float, rng: random.Random) -> str:
    if confusion_rate <= 0:
        return text
    out = []
    for ch in text:
        if ch.isdigit() and rng.random() < confusion_rate:
            out.append(_sample_corruption(ch, rng))
        else:
            out.append(ch)
    return "".join(out)


def _format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def _money_line(idx: int, label: str, cents: int) -> MoneyLine:
    raw = f"{label}  RM {_format_cents(cents)}" if label else f"RM {_format_cents(cents)}"
    return MoneyLine(line_idx=idx, value_cents=cents, raw_text=raw, tags=tag_line(raw))


def _generate_one(rng: random.Random, profile: str) -> Tuple[List[MoneyLine], int, str]:
    """Return (money_lines, gold_total_cents, gold_text)."""
    if profile == "cord_like":
        n_items = rng.randint(2, 6)
    else:  # sroie_like / default
        n_items = rng.randint(2, 5)

    items_cents = [rng.randint(50, 4900) for _ in range(n_items)]
    subtotal = sum(items_cents)

    # Tax: ~50% of receipts have a 6% tax line (so I4 can fire).
    has_tax = rng.random() < 0.5
    tax_cents = round(subtotal * 0.06) if has_tax else 0

    # Cash/change: ~40% (rarer on cord_like).
    has_cash = rng.random() < (0.15 if profile == "cord_like" else 0.40)

    gold_total = subtotal + tax_cents

    lines: List[MoneyLine] = []
    raw_lines: List[str] = ["GROCERY MART", "RECEIPT"]

    for i, c in enumerate(items_cents):
        ml = _money_line(len(lines), f"ITEM-{i+1}", c)
        lines.append(ml)
        raw_lines.append(ml.raw_text)

    # Subtotal line — always present in sroie_like, ~30% in cord_like.
    if profile != "cord_like" or rng.random() < 0.3:
        ml = _money_line(len(lines), "SUBTOTAL", subtotal)
        lines.append(ml)
        raw_lines.append(ml.raw_text)

    if has_tax:
        ml = _money_line(len(lines), "TAX", tax_cents)
        lines.append(ml)
        raw_lines.append(ml.raw_text)

    # Total line — always present (anchors I5 digit-pool soundness).
    ml = _money_line(len(lines), "TOTAL", gold_total)
    lines.append(ml)
    raw_lines.append(ml.raw_text)

    if has_cash:
        # cash >= total; change = cash - total.
        cash = gold_total + rng.randint(0, 5000)
        change = cash - gold_total
        ml_cash = _money_line(len(lines), "CASH", cash)
        lines.append(ml_cash)
        raw_lines.append(ml_cash.raw_text)
        ml_chg = _money_line(len(lines), "CHANGE", change)
        lines.append(ml_chg)
        raw_lines.append(ml_chg.raw_text)

    raw_lines.append("THANK YOU")
    gold_text = "\n".join(raw_lines)
    return lines, gold_total, gold_text


def load_synthetic(n: int = 500, seed: int = 0,
                   profile: str = "sroie_like",
                   confusion_rate: float = 0.05,
                   max_receipts: Optional[int] = None,
                   **_unused) -> List[Receipt]:
    """Build `n` synthetic receipts. Deterministic for a given (n, seed)."""
    if max_receipts is not None:
        n = min(n, max_receipts)
    rng = random.Random(seed)
    out: List[Receipt] = []
    for i in range(n):
        lines, gold, gold_text = _generate_one(rng, profile)
        ocr_text = _corrupt_text(gold_text, confusion_rate, rng)
        out.append(Receipt(
            receipt_id=f"synth-{profile}-{seed}-{i:05d}",
            money_lines=lines,
            gold_total_cents=gold,
            gold_text=gold_text,
            ocr_text=ocr_text,
            meta={"profile": profile, "confusion_rate": confusion_rate},
        ))
    return out
