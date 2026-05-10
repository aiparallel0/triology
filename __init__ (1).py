"""S3 — Empirical character confusion matrix from a real corpus (CORD-v2).

Fills §II's `fig:cord_confusion` figure and underwrites the §VI
empirical-OCR perturbation experiment by providing the confusion
priors S4 will sample from.

Method:

  for each receipt with both `gold_text` and `ocr_text`:
      align the two strings character-by-character using
      Needleman-Wunsch (via difflib.SequenceMatcher.get_opcodes())
      for each aligned (gold_char, ocr_char) pair where they differ:
          confusion[gold_char][ocr_char] += 1
      restrict to digit-vs-digit substitutions (0..9 x 0..9)

  normalize each row so confusion[g][:] sums to 1.

The output is:

  results/s3_cord_confusion.json   10x10 row-stochastic matrix + raw counts
  results/s3_cord_confusion.svg    heatmap, IEEE-figure-grade

The heatmap palette is white-to-dark to stay legible in greyscale
and the diagonal (gold == ocr, no-change) is set to NaN so it doesn't
dominate the colour scale.

Note: synthetic-mode confusion uses the priors hardcoded in
synthetic_loader._maybe_corrupt_digit. The smoke-test recovery of
those priors verifies the alignment code path correctness end-to-end.
"""
from __future__ import annotations
import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from ..data import load_corpus

DIGITS = "0123456789"
RESULTS = Path("results")


def align_chars(gold: str, ocr: str) -> List[Tuple[str, str]]:
    """Return list of (gold_char, ocr_char) aligned pairs.

    Uses difflib.SequenceMatcher with autojunk disabled. Equal regions
    map char-to-char; replace regions map char-to-char up to the
    shorter of the two segments (extra chars on either side are
    treated as insertions/deletions and dropped — they don't carry
    "this digit was confused for that digit" information).
    """
    sm = difflib.SequenceMatcher(None, gold, ocr, autojunk=False)
    pairs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                pairs.append((gold[i1 + k], ocr[j1 + k]))
        elif tag == "replace":
            n = min(i2 - i1, j2 - j1)
            for k in range(n):
                pairs.append((gold[i1 + k], ocr[j1 + k]))
        # insert / delete: skip — those are not substitution events
    return pairs


def collect_confusion(receipts) -> Tuple[np.ndarray, int, int]:
    """Walk receipts, collect digit-vs-digit confusion counts.

    Returns:
        counts : 10x10 int matrix, counts[g][o] = count of (gold=g, ocr=o)
        n_pairs_total : total digit pairs aligned
        n_skipped     : receipts skipped due to missing texts
    """
    counts = np.zeros((10, 10), dtype=np.int64)
    n_pairs_total = 0
    n_skipped = 0
    for r in receipts:
        if r.gold_text is None or r.ocr_text is None:
            n_skipped += 1
            continue
        for g, o in align_chars(r.gold_text, r.ocr_text):
            if g in DIGITS and o in DIGITS:
                counts[int(g), int(o)] += 1
                n_pairs_total += 1
    return counts, n_pairs_total, n_skipped


def row_normalize(counts: np.ndarray) -> np.ndarray:
    """Row-stochastic normalization: P(ocr | gold)."""
    out = np.zeros_like(counts, dtype=np.float64)
    row_sums = counts.sum(axis=1, keepdims=True)
    nz = (row_sums.flatten() > 0)
    out[nz] = counts[nz] / row_sums[nz]
    return out


def render_heatmap_svg(matrix: np.ndarray, counts: np.ndarray,
                       outpath: Path, title: str = "") -> None:
    """10x10 heatmap, white -> dark navy. Diagonal greyed-out."""
    cell = 36
    pad_left, pad_top, pad_right, pad_bot = 50, 60, 30, 50
    width = pad_left + 10 * cell + pad_right
    height = pad_top + 10 * cell + pad_bot

    # Mask diagonal for color scale: off-diagonal max
    off_diag = matrix.copy()
    np.fill_diagonal(off_diag, np.nan)
    vmax = float(np.nanmax(off_diag)) if np.any(~np.isnan(off_diag)) else 1.0
    if vmax <= 0:
        vmax = 1.0

    def colormap(v: float) -> str:
        # Linear white (255,255,255) -> navy (31,58,147)
        if np.isnan(v):
            return "#eaeaea"
        t = min(v / vmax, 1.0)
        r = int(255 + (31  - 255) * t)
        g = int(255 + (58  - 255) * t)
        b = int(255 + (147 - 255) * t)
        return f"rgb({r},{g},{b})"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'font-family="serif" font-size="11">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="{width/2}" y="22" text-anchor="middle" font-weight="bold" '
        f'font-size="13">{title or "Empirical digit confusion matrix"}</text>',
        f'<text x="{width/2}" y="40" text-anchor="middle" font-style="italic" '
        f'font-size="10">P(ocr-digit | gold-digit), n_pairs = {int(counts.sum())}</text>',
    ]
    # Cells
    for g in range(10):
        for o in range(10):
            x = pad_left + o * cell
            y = pad_top + g * cell
            v = matrix[g, o] if g != o else float("nan")
            fill = colormap(v)
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                         f'fill="{fill}" stroke="white" stroke-width="0.5"/>')
            # Annotate non-trivial cells
            if g != o and matrix[g, o] >= max(0.02, vmax * 0.15):
                txt_color = "white" if matrix[g, o] > vmax * 0.5 else "black"
                parts.append(f'<text x="{x + cell/2}" y="{y + cell/2 + 3}" '
                             f'text-anchor="middle" fill="{txt_color}">'
                             f'{matrix[g, o]*100:.0f}</text>')
    # Axis labels
    for i in range(10):
        # Column labels (OCR digits)
        parts.append(f'<text x="{pad_left + i*cell + cell/2}" y="{pad_top - 6}" '
                     f'text-anchor="middle">{i}</text>')
        # Row labels (gold digits)
        parts.append(f'<text x="{pad_left - 8}" y="{pad_top + i*cell + cell/2 + 4}" '
                     f'text-anchor="end">{i}</text>')
    parts.append(f'<text x="{pad_left + 5*cell}" y="{pad_top + 10*cell + 30}" '
                 f'text-anchor="middle">OCR digit</text>')
    parts.append(f'<text x="20" y="{pad_top + 5*cell}" text-anchor="middle" '
                 f'transform="rotate(-90 20 {pad_top + 5*cell})">Gold digit</text>')
    parts.append('</svg>')
    outpath.write_text("\n".join(parts))


def parse_args():
    ap = argparse.ArgumentParser(description="S3: digit confusion matrix")
    ap.add_argument("--corpus", choices=["cord", "synthetic"],
                    default="synthetic",
                    help="Real-data run uses --corpus cord; "
                         "synthetic mode injects priors for round-trip test")
    ap.add_argument("--path", default=None)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--confusion_rate", type=float, default=0.05,
                    help="synthetic only: per-digit corruption rate")
    ap.add_argument("--out_json", default="results/s3_cord_confusion.json")
    ap.add_argument("--out_svg",  default="results/s3_cord_confusion.svg")
    return ap.parse_args()


def main():
    args = parse_args()
    RESULTS.mkdir(exist_ok=True)

    if args.corpus == "synthetic":
        recs = load_corpus("synthetic", n=args.n, seed=args.seed,
                           profile="sroie_like",
                           confusion_rate=args.confusion_rate,
                           max_receipts=args.max)
        title = (f"Synthetic confusion matrix (n_pairs={args.n} receipts, "
                 f"rate={args.confusion_rate})")
    else:
        recs = load_corpus("cord", path=args.path,
                           max_receipts=args.max)
        title = "CORD-v2 empirical digit confusion matrix"

    counts, n_pairs, n_skipped = collect_confusion(recs)
    P = row_normalize(counts)

    print(f"[s3] aligned pairs: {n_pairs}, skipped receipts: {n_skipped}",
          file=sys.stderr)

    out = {
        "n_aligned_pairs": int(n_pairs),
        "n_skipped_receipts": int(n_skipped),
        "counts":         counts.tolist(),
        "P_ocr_given_gold": P.tolist(),
        "title": title,
    }
    Path(args.out_json).write_text(json.dumps(out, indent=2))
    render_heatmap_svg(P, counts, Path(args.out_svg), title=title)
    print(f"[s3] wrote {args.out_json}, {args.out_svg}", file=sys.stderr)

    # Print top off-diagonal confusions for sanity check
    pairs = []
    for g in range(10):
        for o in range(10):
            if g != o and counts[g, o] > 0:
                pairs.append((g, o, P[g, o], counts[g, o]))
    pairs.sort(key=lambda x: -x[2])
    print("\nTop 10 confusions (P(ocr | gold), count):")
    for g, o, p, c in pairs[:10]:
        print(f"  {g} -> {o}:  {p*100:5.2f}%   ({c})")


if __name__ == "__main__":
    main()
