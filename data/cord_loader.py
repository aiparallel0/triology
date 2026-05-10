"""CORD-v2 (Consolidated Receipt Dataset) loader.

CORD ships through the HuggingFace `datasets` hub as
`naver-clova-ix/cord-v2` and a local copy under `<root>` follows:

    <root>/
      train/  test/  validation/        # parquet shards from `datasets.save_to_disk`

If `datasets` is installed and the path looks like a HF dataset root
we load via `datasets.load_from_disk`. Otherwise we accept a directory
of one-receipt-per-JSON files (the "expanded" format some users prefer).

Each example carries a `gt_parse` JSON tree with a `valid_line` array
whose entries have `words[i].text` and structured category labels. The
total is the line whose category contains "total_price" or
"menu.total_price"; the digit string is parsed.

CORD-v2 is dominantly Indonesian / Korean receipts, where prices look
like "12,500" (integer rupiah/won, comma is the thousands separator,
no decimal) — distinct from SROIE's `RM 12.50` decimal-based money.
We use a CORD-specific money parser:

  * "12,500" -> 12500          (integer, comma is thousands sep)
  * "60,000" -> 60000
  * "12.50"  -> 1250           (decimal — store as centi-units)
  * "1,250.00" -> 125000

The verifier doesn't care which units a receipt's values are in as long
as items + tau == gold within EPS_CENTS=2 *in the same units*. Each
receipt's parser is consistent within itself, so I3 reachability and
the digit-pool checks all work.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .types import Receipt, MoneyLine

try:
    from ..core.keyword_tagger import tag_line
except (ImportError, ValueError):
    def tag_line(text: str) -> List[str]:
        return []


# Decimal-style money: "DDD.DD", "1,250.00".
_DEC_MONEY_RE = re.compile(
    r"(?<![\d.])(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})(?!\d)"
)
# Integer-style money with thousands separator: "12,500", "1,234,567".
_INT_THOUSANDS_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:,\d{3})+)(?![\d.,])"
)
# Integer-style money without separator (>=4 digits): "60000".
_INT_BARE_RE = re.compile(
    r"(?<![\d.,])(\d{4,})(?!\d)"
)


def _parse_cord_money(text: str) -> Optional[int]:
    """Parse a CORD price string. Returns integer in the receipt's natural
    minor unit (centi-USD when decimal, whole-rupiah when integer)."""
    s = text.strip()
    if not s:
        return None
    m = _DEC_MONEY_RE.search(s)
    if m:
        whole = m.group(1).replace(",", "")
        try:
            return int(whole) * 100 + int(m.group(2))
        except ValueError:
            return None
    m = _INT_THOUSANDS_RE.search(s)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            return None
    m = _INT_BARE_RE.search(s)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _extract_money_lines_cord(raw_lines: List[str]) -> List[MoneyLine]:
    """CORD-aware money line extractor.

    Same convention as `core.money_lines.extract_money_lines`: at most
    one MoneyLine per OCR line, taking the rightmost numeric value
    (which by SROIE/CORD layout is the line-total when one is present).
    """
    out: List[MoneyLine] = []
    for idx, line in enumerate(raw_lines):
        # Prefer decimal first, then integer-with-thousands, then bare int.
        best = None
        for pattern, is_decimal in (
            (_DEC_MONEY_RE, True),
            (_INT_THOUSANDS_RE, False),
            (_INT_BARE_RE, False),
        ):
            matches = list(pattern.finditer(line))
            if not matches:
                continue
            best = (matches[-1], is_decimal)
            break
        if best is None:
            continue
        m, is_decimal = best
        if is_decimal:
            whole = m.group(1).replace(",", "")
            try:
                value = int(whole) * 100 + int(m.group(2))
            except ValueError:
                continue
        else:
            try:
                value = int(m.group(1).replace(",", ""))
            except ValueError:
                continue
        out.append(MoneyLine(
            line_idx=idx,
            value_cents=value,
            raw_text=line,
            tags=tag_line(line),
        ))
    return out


def _walk(d: Any) -> Iterable[Dict[str, Any]]:
    """Yield every dict node in a CORD `gt_parse` tree."""
    if isinstance(d, dict):
        yield d
        for v in d.values():
            yield from _walk(v)
    elif isinstance(d, list):
        for item in d:
            yield from _walk(item)


def _extract_total(gt_parse: Dict[str, Any]) -> Optional[int]:
    """Find the receipt's total. Prefers menu.total_price.total_price."""
    candidates: List[str] = []
    for node in _walk(gt_parse):
        for key, val in node.items():
            if not isinstance(val, str):
                continue
            if "total_price" in key or key == "total":
                candidates.append(val)
    for raw in candidates:
        cents = _parse_cord_money(raw)
        if cents is not None:
            return cents
    return None


def _to_lines(words: List[Dict[str, Any]]) -> List[str]:
    return [w.get("text", "") for w in words if w.get("text")]


def _receipts_from_hf(ds, max_receipts: Optional[int]) -> List[Receipt]:
    out: List[Receipt] = []
    for i, ex in enumerate(ds):
        if max_receipts is not None and i >= max_receipts:
            break
        gt_raw = ex.get("ground_truth")
        try:
            gt = json.loads(gt_raw) if isinstance(gt_raw, str) else gt_raw
        except json.JSONDecodeError:
            continue
        if not isinstance(gt, dict):
            continue
        gt_parse = gt.get("gt_parse", gt)
        gold = _extract_total(gt_parse)
        if gold is None:
            continue
        valid_lines = gt.get("valid_line", [])
        raw_lines: List[str] = []
        for vl in valid_lines:
            words = vl.get("words", [])
            line_text = " ".join(_to_lines(words))
            if line_text:
                raw_lines.append(line_text)
        money_lines = _extract_money_lines_cord(raw_lines)
        gold_text = "\n".join(raw_lines) if raw_lines else None
        out.append(Receipt(
            receipt_id=f"cord-{i:05d}",
            money_lines=money_lines,
            gold_total_cents=gold,
            gold_text=gold_text,
            ocr_text=gold_text,
            meta={"source": "cord-v2"},
        ))
    return out


def load_cord(path: str, max_receipts: Optional[int] = None,
              split: str = "test", **_unused) -> List[Receipt]:
    """Load CORD-v2 receipts from `path`.

    `path` may be:
      * a directory written by `datasets.save_to_disk` (looks for `<path>/<split>/`)
      * a directory of one-JSON-per-receipt files (each carrying `gt_parse`)
    """
    root = Path(path)
    if not root.exists():
        raise FileNotFoundError(f"CORD path missing: {root}")

    hf_subdir = root / split
    if hf_subdir.exists() and (hf_subdir / "dataset_info.json").exists():
        try:
            from datasets import load_from_disk  # type: ignore
        except ImportError as e:
            raise ImportError(
                "CORD-v2 saved-to-disk loading requires the `datasets` "
                "package. `pip install datasets`."
            ) from e
        ds = load_from_disk(str(hf_subdir))
        return _receipts_from_hf(ds, max_receipts)

    json_files = sorted(root.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(
            f"CORD path {root} has neither a HF split nor *.json files. "
            f"Expected either '{root}/{split}/' (datasets format) or "
            f"'*.json' files containing `gt_parse`."
        )

    out: List[Receipt] = []
    for jp in json_files:
        if max_receipts is not None and len(out) >= max_receipts:
            break
        try:
            obj = json.loads(jp.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        gt_parse = obj.get("gt_parse", obj)
        gold = _extract_total(gt_parse)
        if gold is None:
            continue
        raw_lines: List[str] = []
        for vl in obj.get("valid_line", []):
            words = vl.get("words", [])
            line_text = " ".join(_to_lines(words))
            if line_text:
                raw_lines.append(line_text)
        money_lines = _extract_money_lines_cord(raw_lines)
        gold_text = "\n".join(raw_lines) if raw_lines else None
        out.append(Receipt(
            receipt_id=f"cord-{jp.stem}",
            money_lines=money_lines,
            gold_total_cents=gold,
            gold_text=gold_text,
            ocr_text=gold_text,
            meta={"source": "cord-v2", "json": str(jp)},
        ))
    return out
