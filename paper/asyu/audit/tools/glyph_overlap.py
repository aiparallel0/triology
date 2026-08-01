#!/usr/bin/env python3
"""Overlapping-text check -- reads the rendered PDF, not the source.

Text that prints on top of other text is invisible to every source-level
check in this kit. It has three causes, and this paper hit all three:

  1. A box that cannot break.  \\chgi is an \\fcolorbox; a multi-sentence span
     inside one sets as a single unbreakable horizontal box that runs past the
     column edge and prints over the next column.
  2. A heading too long for its column.  Renaming the subsections to RQ form
     made one of them 28pt wider than the column.
  3. A figure label colliding with itself.  A two-line matplotlib tick label
     at 8pt had its second line printing over its first, in all three panels.

Block-level comparison is not enough: pymupdf groups adjacent labels into one
block, so real collisions hide inside a block and spurious ones appear between
blocks that merely interleave. Compare WORDS.

Reports two classes separately, because they are different bugs:
  COLUMN   a text block wider than a column in a two-column layout
  GLYPH    two words whose boxes intersect

Exit 0 when clean, 1 when something overlaps, 2 when the PDF has no text at
all. Needs pymupdf; SKIPs (exit 3) without it rather than passing silently.

Usage: glyph_overlap.py <file.pdf> [<file.pdf> ...] [--col-width 260]
"""
import sys

try:
    import fitz
except ImportError:
    print("SKIP: pymupdf not installed -- overlapping text NOT verified")
    sys.exit(3)


def inter(a, b):
    x = min(a[2], b[2]) - max(a[0], b[0])
    y = min(a[3], b[3]) - max(a[1], b[1])
    return x * y if x > 0 and y > 0 else 0


def real_collision(a, b):
    """True when two word boxes genuinely print over each other.

    Inline math defeats an area threshold: the box around
    $\\in\\mathbb{Q}_{\\geq 0}$ or $10^2$--$10^3$ is taller and wider than its
    glyphs and grazes the word beside it. The known-good original of this paper
    had eleven such pairs and no visible defect, so a bare threshold reports
    eleven false alarms and the check gets ignored -- the failure mode this kit
    exists to avoid. Comparing vertical centres does not separate them either,
    because the math box is the taller one and its centre is offset.

    What does separate them is the SHAPE of the intersection:

      side by side (math graze)   wide y-overlap, almost no x-overlap
      stacked (real collision)    almost full x-overlap, thin y-overlap

    A two-line label printing over itself, or text from an unbreakable box
    landing on the next column, sits nearly on top of the word it hits. Require
    both axes to overlap substantially relative to the smaller word.
    """
    x = min(a[2], b[2]) - max(a[0], b[0])
    y = min(a[3], b[3]) - max(a[1], b[1])
    if x <= 0 or y <= 0:
        return False
    wmin = min(a[2] - a[0], b[2] - b[0]) or 1
    hmin = min(a[3] - a[1], b[3] - b[1]) or 1
    return (x / wmin) > 0.55 and (y / hmin) > 0.18


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    col = 260
    if '--col-width' in argv:
        col = float(argv[argv.index('--col-width') + 1])
    if not args:
        print(__doc__)
        return 2

    rc = 0
    for path in args:
        try:
            doc = fitz.open(path)
        except Exception as exc:                       # noqa: BLE001
            print(f"SKIP: cannot open {path}: {exc}")
            return 3

        if not any(p.get_text().strip() for p in doc):
            print(f"{path}: NO TEXT AT ALL -- wrong file? check did not run")
            return 2

        glyph, wide = [], []
        for pno, page in enumerate(doc, 1):
            words = page.get_text("words")
            for i in range(len(words)):
                for j in range(i + 1, len(words)):
                    if real_collision(words[i][:4], words[j][:4]):
                        glyph.append((pno, inter(words[i][:4], words[j][:4]),
                                      words[i][4], words[j][4]))
            # A full-width block is legitimate for figure*/table* and the
            # title; anything else that wide is running out of its column.
            for b in page.get_text("blocks"):
                t = b[4].strip()
                if not t or b[1] < 120:
                    continue
                if (b[2] - b[0]) > col * 1.15 and not t.startswith(
                        ('Fig.', 'TABLE', 'Figure')):
                    wide.append((pno, b[2] - b[0], t))

        print(f"{path}  ({doc.page_count} pages)")
        if wide:
            print(f"  COLUMN ({len(wide)}): text wider than a column -- an "
                  f"unbreakable box or an over-long heading")
            for pno, w, t in wide[:8]:
                print(f"    p{pno}  {w:.0f}pt  {' '.join(t.split())[:62]}")
            rc = 1
        else:
            print("  COLUMN: none")

        if glyph:
            print(f"  GLYPH ({len(glyph)}): words printing on top of each other")
            seen = set()
            for pno, ov, a, b in glyph:
                if (a, b) in seen:
                    continue
                seen.add((a, b))
                print(f"    p{pno}  area {ov:5.1f}  {a!r} / {b!r}")
                if len(seen) >= 8:
                    break
            rc = 1
        else:
            print("  GLYPH: none")

    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
