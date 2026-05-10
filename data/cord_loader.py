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
"menu.total_price"; the digit string is parsed to cents.

For the smoke test we never reach this loader (synthetic only), but
if `datasets` is unavailable we raise a helpful error rather than
silently returning an empty corpus.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .types import Receipt

_TOTAL_RE = re.compile(r"(\d{1,3}(?:[,.]\d{3})*|\d+)[.,](\d{2})")


def _walk(d: Any) -> Iterable[Dict[str, Any]]:
    """Yield every dict node in a CORD `gt_parse` tree."""
    if isinstance(d, dict):
        yield d
        for v in d.values():
            yield from _walk(v)
    elif isinstance(d, list):
        for item in d:
            yield from _walk(item)


def _extract_total_cents(gt_parse: Dict[str, Any]) -> Optional[int]:
    # Prefer menu.total_price.total_price if present, else any *.total_price.
    candidates: List[str] = []
    for node in _walk(gt_parse):
        for key, val in node.items():
            if not isinstance(val, str):
                continue
            if "total_price" in key or "total" == key:
                candidates.append(val)
    for raw in candidates:
        m = _TOTAL_RE.search(raw.replace(" ", ""))
        if m is None:
            continue
        whole = m.group(1).replace(",", "").replace(".", "")
        # If the whole part has its own '.' we already stripped it; the
        # last 2 digits are cents.
        try:
            return int(whole) * 100 + int(m.group(2))
        except ValueError:
            continue
    return None


def _to_lines(words: List[Dict[str, Any]]) -> List[str]:
    return [w.get("text", "") for w in words if w.get("text")]


def _receipts_from_hf(ds, max_receipts: Optional[int]) -> List[Receipt]:
    from ..core.money_lines import extract_money_lines

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
        gold = _extract_total_cents(gt_parse)
        if gold is None:
            continue
        # Reconstruct OCR text from valid_line if present.
        valid_lines = gt.get("valid_line", [])
        raw_lines: List[str] = []
        for vl in valid_lines:
            words = vl.get("words", [])
            line_text = " ".join(_to_lines(words))
            if line_text:
                raw_lines.append(line_text)
        money_lines = extract_money_lines(raw_lines)
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

    # HuggingFace `datasets` save_to_disk layout
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

    # Plain JSON directory
    json_files = sorted(root.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(
            f"CORD path {root} has neither a HF split nor *.json files. "
            f"Expected either '{root}/{split}/' (datasets format) or "
            f"'*.json' files containing `gt_parse`."
        )

    from ..core.money_lines import extract_money_lines

    out: List[Receipt] = []
    for jp in json_files:
        if max_receipts is not None and len(out) >= max_receipts:
            break
        try:
            obj = json.loads(jp.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        gt_parse = obj.get("gt_parse", obj)
        gold = _extract_total_cents(gt_parse)
        if gold is None:
            continue
        raw_lines: List[str] = []
        for vl in obj.get("valid_line", []):
            words = vl.get("words", [])
            line_text = " ".join(_to_lines(words))
            if line_text:
                raw_lines.append(line_text)
        money_lines = extract_money_lines(raw_lines)
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
