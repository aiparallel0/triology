"""Audit which OCR lines fire which keyword tags on a corpus.

Used to verify Paper 1 / Paper 3 §IV table I1/I2 availability numbers
when they deviate from the published reference. Two views:

  Tag counts table — how many money lines carry each tag, plus the
  number of receipts on which each identity is "available".

  Per-tag examples — sample raw text of money lines that triggered a
  given tag. Useful for spotting false positives (e.g. "exchange
  policy" matching the "change" lexicon).

Usage:
    python -m <pkg>.scripts.debug_tagger --corpus cord \\
        --path /workspace/datasets/cord-v2 --max 20

    # Filter to a single tag:
    python -m <pkg>.scripts.debug_tagger --corpus cord \\
        --path /workspace/datasets/cord-v2 --tag cash --max 50
"""
from __future__ import annotations
import argparse
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from ..data import load_corpus
from ..core.identities import IDENTITY_NAMES, is_available, is_accepted
from ..core.keyword_tagger import (
    LEX_CASH, LEX_CHANGE, LEX_SUBTOTAL, LEX_TAX, LEX_SERVICE,
    LEX_DISCOUNT, LEX_TOTAL,
)


_LEX_BY_TAG = {
    "cash":     LEX_CASH,
    "change":   LEX_CHANGE,
    "subtotal": LEX_SUBTOTAL,
    "tax":      LEX_TAX,
    "service":  LEX_SERVICE,
    "discount": LEX_DISCOUNT,
    "total":    LEX_TOTAL,
}


def parse_args():
    ap = argparse.ArgumentParser(description="Audit keyword-tagger firings")
    ap.add_argument("--corpus", required=True,
                    choices=["sroie", "cord", "synthetic"])
    ap.add_argument("--path", default=None,
                    help="corpus root for sroie/cord")
    ap.add_argument("--n", type=int, default=500,
                    help="synthetic only: number of receipts")
    ap.add_argument("--max_receipts", type=int, default=None,
                    help="cap real-corpus N")
    ap.add_argument("--max", type=int, default=20,
                    help="max examples per tag to print")
    ap.add_argument("--tag", default=None,
                    help="filter to a single tag (cash, change, subtotal, ...)")
    ap.add_argument("--show_lexicon", action="store_true",
                    help="print the lexicon strings used per tag")
    return ap.parse_args()


def main():
    args = parse_args()
    receipts = load_corpus(args.corpus, path=args.path,
                           n=args.n, max_receipts=args.max_receipts)
    print(f"[debug] loaded {len(receipts)} receipts from {args.corpus}",
          file=sys.stderr)

    if args.show_lexicon:
        print("\nKeyword lexicons (substring match, case-insensitive):")
        for tag, lex in _LEX_BY_TAG.items():
            print(f"  {tag:>10}: {list(lex)}")

    tag_line_count = Counter()
    tag_receipt_count = Counter()
    examples: Dict[str, List[Tuple[str, int, int, str]]] = defaultdict(list)

    for r in receipts:
        seen_tags = set()
        for ml in r.money_lines:
            for tag in ml.tags:
                tag_line_count[tag] += 1
                seen_tags.add(tag)
                if args.tag and tag != args.tag:
                    continue
                examples[tag].append(
                    (r.receipt_id, ml.line_idx, ml.value_cents, ml.raw_text)
                )
        for tag in seen_tags:
            tag_receipt_count[tag] += 1

    avail_count = Counter()
    sound_count = Counter()
    for r in receipts:
        for ident in IDENTITY_NAMES:
            if is_available(ident, r):
                avail_count[ident] += 1
                if is_accepted(ident, r, r.gold_total_cents):
                    sound_count[ident] += 1

    n = len(receipts)
    print(f"\nTag firings across {n} receipts:")
    print(f"  {'tag':<10}  {'#lines':>7}  {'#receipts':>10}")
    for tag in ("cash", "change", "subtotal", "total", "tax",
                "service", "discount"):
        print(f"  {tag:<10}  {tag_line_count[tag]:>7}  "
              f"{tag_receipt_count[tag]:>10}  "
              f"({tag_receipt_count[tag]/max(1,n)*100:5.1f}% receipts)")

    print(f"\nIdentity availability / soundness:")
    print(f"  {'ident':<6}  {'avail':>6}  {'sound|avail':>12}")
    for ident in IDENTITY_NAMES:
        a = avail_count[ident]
        s = sound_count[ident]
        a_pct = a / max(1, n) * 100
        s_pct = s / max(1, a) * 100 if a else 0.0
        print(f"  {ident:<6}  {a_pct:>5.1f}%  {s_pct:>11.1f}%  "
              f"({s}/{a} sound, {a}/{n} avail)")

    tags_to_show = [args.tag] if args.tag else list(_LEX_BY_TAG.keys())
    print(f"\nUp to {args.max} examples per tag:")
    for tag in tags_to_show:
        ex = examples.get(tag, [])
        if not ex:
            continue
        print(f"\n[{tag}]  ({len(ex)} total firings)")
        for rid, idx, cents, text in ex[:args.max]:
            print(f"  {rid}:line{idx}  cents={cents}  {text!r}")


if __name__ == "__main__":
    main()
