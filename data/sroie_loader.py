"""SROIE Task-3 (Scanned Receipts OCR + Information Extraction) loader.

Expected on-disk layout (the canonical SROIE Task-3 release):

    <root>/
      img/      0001.jpg, 0002.jpg, ...
      box/      0001.txt, ...     # Task-1 OCR boxes (x1,y1,...,x8,y8,text)
      entities/ 0001.txt, ...     # Task-3 ground truth as JSON

Each `entities/*.txt` is a JSON object with at least the field `total`
(string like "12.50"), and usually also `company`, `date`, `address`.
Each `box/*.txt` line gives one OCR token with its bounding box; we
collapse boxes by line (rounded mid-y) and concatenate text.

Returns one `Receipt` per file pair. `gold_total_cents` comes from the
`total` entity; `money_lines` come from the box file (re-parsed by
`core.money_lines.extract_money_lines`).

Raises FileNotFoundError if `<root>/entities/` is empty (the most common
"forgot to download Task-3" failure mode).
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from typing import Iterator, List, Optional

from .types import Receipt

_BOX_LINE_RE = re.compile(r"^(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(.*)$")
_TOTAL_RE = re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})")


def _parse_total_to_cents(s: str) -> Optional[int]:
    if s is None:
        return None
    m = _TOTAL_RE.search(s.replace(" ", ""))
    if m is None:
        return None
    whole = m.group(1).replace(",", "")
    return int(whole) * 100 + int(m.group(2))


def _parse_entities_text(text: str) -> dict:
    """Parse a SROIE entities file. Accepts either:
        * JSON object: '{"company": "...", "total": "12.50", ...}'
        * KV-text:     'company: ...\\ndate: ...\\ntotal: 12.50'

    Skips lines that look like Task-1 box-file rows
    ('123,456,...,LABEL:VALUE'), which the public flat-layout mirror
    sometimes mixes into the entities directory.
    """
    s = text.strip()
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return {str(k).lower(): str(v) for k, v in obj.items()}
        except json.JSONDecodeError:
            pass
    out: dict = {}
    for line in s.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        head = k.split(",", 1)[0].strip()
        if "," in k and head.isdigit():
            # Task-1 box-file line ("x1,y1,...,LABEL:VALUE") — skip.
            continue
        key = k.strip().lower()
        if key:
            out[key] = v.strip()
    return out


def _read_box_file(path: Path) -> List[str]:
    """Collapse a SROIE box file into one OCR text per receipt line."""
    rows: List[tuple] = []  # (mid_y, x1, text)
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _BOX_LINE_RE.match(raw)
        if m is None:
            continue
        ys = [int(m.group(i)) for i in (2, 4, 6, 8)]
        x1 = int(m.group(1))
        text = m.group(9).strip()
        if not text:
            continue
        mid_y = sum(ys) // 4
        rows.append((mid_y, x1, text))
    rows.sort(key=lambda t: (t[0] // 10, t[1]))
    grouped: List[str] = []
    cur_band: List[str] = []
    cur_y = None
    for mid_y, _x1, text in rows:
        band = mid_y // 10
        if cur_y is None or band == cur_y:
            cur_band.append(text)
        else:
            grouped.append(" ".join(cur_band))
            cur_band = [text]
        cur_y = band
    if cur_band:
        grouped.append(" ".join(cur_band))
    return grouped


def load_sroie(path: str, max_receipts: Optional[int] = None,
               seed: int = 0, **_unused) -> List[Receipt]:
    """Load SROIE Task-3 receipts from `path` (the dataset root)."""
    # Lazy import to avoid circular imports at module-load time.
    from ..core.money_lines import extract_money_lines

    root = Path(path)
    ent_dir = root / "entities"
    box_dir = root / "box"
    if not ent_dir.exists():
        raise FileNotFoundError(
            f"SROIE entities directory missing: {ent_dir}. Expected layout "
            f"{root}/{{img,box,entities}}/."
        )

    receipts: List[Receipt] = []
    ent_files = sorted(list(ent_dir.glob("*.txt")) + list(ent_dir.glob("*.json")))
    for ent_path in ent_files:
        if max_receipts is not None and len(receipts) >= max_receipts:
            break
        ent = _parse_entities_text(
            ent_path.read_text(encoding="utf-8", errors="replace")
        )
        if not ent:
            continue
        gold_cents = _parse_total_to_cents(ent.get("total", ""))
        if gold_cents is None:
            continue
        rid = ent_path.stem
        box_path = box_dir / f"{rid}.txt"
        raw_lines = _read_box_file(box_path) if box_path.exists() else []
        money_lines = extract_money_lines(raw_lines)
        gold_text = "\n".join(raw_lines) if raw_lines else None
        receipts.append(Receipt(
            receipt_id=f"sroie-{rid}",
            money_lines=money_lines,
            gold_total_cents=gold_cents,
            gold_text=gold_text,
            ocr_text=gold_text,  # SROIE has no separate "true" text
            meta={"source": "sroie", "image": str(root / "img" / f"{rid}.jpg")},
        ))
    return receipts
