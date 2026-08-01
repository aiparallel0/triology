#!/usr/bin/env python3
"""Repeated-sentence check -- reads the rendered PDF, not the source.

A sentence can reach the page twice without appearing twice in main.tex.
Footnote text pasted into the body during an edit, a caption restating its
own paragraph, a limitation repeated in Discussion and Results, a claim
copied across sections when a paragraph moved: each is one sentence in two
places, and none of them is a LaTeX error. The compiler is happy, every
source-level check passes, and the reader sees the paper say the same thing
twice.

Source-level grep does not find these. The two copies are usually reworded
("names the verifier" against "denotes the verifier"), so an exact string
search over the .tex misses them, and text that arrives from a macro or a
generated file is not in the .tex at all. What the reader sees is the PDF,
so the PDF is what this reads.

Two classes, reported separately:
  EXACT  the same normalised sentence printed twice
  NEAR   two sentences sharing enough content words to be the same claim

NEAR uses Jaccard over content words. Set the threshold too low and every
pair of sentences about precision and coverage matches; 0.72 was chosen
against this paper, where the highest legitimate pair sits near 0.6 and the
known restatements sat above 0.8.

Exit 0 when clean, 1 on a repeat, 2 when the PDF has no text -- an empty
result here is indistinguishable from a passing one otherwise. SKIPs (3)
without pymupdf rather than passing silently.

Usage: duplicate_text.py <file.pdf> [--near 0.72] [--min-words 8]
"""
import re
import sys

try:
    import fitz
except ImportError:
    print("SKIP: pymupdf not installed -- repeated text NOT verified")
    sys.exit(3)

STOP = {'the', 'a', 'an', 'of', 'to', 'in', 'is', 'it', 'and', 'or', 'that',
        'this', 'we', 'for', 'on', 'at', 'as', 'by', 'with', 'not', 'but',
        'its', 'be', 'are', 'was', 'from', 'than', 'so', 'which', 'when'}


def sentences(text):
    """Split into sentences, honouring two PDF-specific boundaries.

    A footnote carries no terminating period on the line above it, so the
    body text running into the page break glues straight onto the footnote:
    "...statistically orthogonal to 1Throughout, sigma names the verifier..."
    as one 33-word blob. That buried the very repeat this check exists to
    find, so a footnote marker (a digit wedged between a lowercase letter
    and a capitalised word) starts a new sentence. Column and block breaks
    are handled by the caller feeding blocks rather than whole pages.
    """
    text = re.sub(r'-\n', '', text)          # undo hyphenation at line breaks
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(?<=[a-z,;:)])\s?\d{1,2}(?=[A-Z][a-z])', '. ', text)
    text = re.sub(r'^\s*\d{1,2}(?=[A-Z][a-z])', '', text)   # marker at block start
    for s in re.split(r'(?<=[.!?])\s+(?=[A-Z(])', text):
        s = s.strip()
        if s:
            yield s


def norm(s):
    return re.sub(r'[^a-z0-9 ]', '', s.lower()).strip()


def content(s):
    return {w for w in norm(s).split() if w not in STOP and len(w) > 2}


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    near = 0.72
    minw = 8
    if '--near' in argv:
        near = float(argv[argv.index('--near') + 1])
    if '--min-words' in argv:
        minw = int(argv[argv.index('--min-words') + 1])
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

        # Per block, not per page: a two-column layout interleaves columns in
        # the page-level text stream, which fuses the tail of one column onto
        # the head of the next and invents sentences that were never printed.
        sents = []
        for pno, page in enumerate(doc, 1):
            for b in page.get_text("blocks"):
                for s in sentences(b[4]):
                    if len(s.split()) >= minw:
                        sents.append((pno, s))
        if not sents:
            print(f"{path}: NO TEXT AT ALL -- wrong file? check did not run")
            return 2

        print(f"{path}  ({doc.page_count} pages, {len(sents)} sentences)")

        seen, exact = {}, []
        for pno, s in sents:
            k = norm(s)
            if k in seen:
                exact.append((seen[k], pno, s))
            else:
                seen[k] = pno

        if exact:
            print(f"  EXACT ({len(exact)}): the same sentence printed twice")
            for p1, p2, s in exact[:6]:
                print(f"    p{p1} and p{p2}: {s[:90]}")
            rc = 1
        else:
            print("  EXACT: none")

        bags = [(p, s, content(s)) for p, s in sents]
        hits = []
        for i in range(len(bags)):
            p1, s1, c1 = bags[i]
            if len(c1) < 5:
                continue
            for j in range(i + 1, len(bags)):
                p2, s2, c2 = bags[j]
                if len(c2) < 5:
                    continue
                if norm(s1) == norm(s2):
                    continue                    # already reported as EXACT
                u = c1 | c2
                if u and len(c1 & c2) / len(u) >= near:
                    hits.append((p1, p2, s1, s2))

        if hits:
            print(f"  NEAR ({len(hits)}): the same claim stated twice "
                  f"(Jaccard >= {near})")
            for p1, p2, s1, s2 in hits[:6]:
                print(f"    p{p1}: {s1[:86]}")
                print(f"    p{p2}: {s2[:86]}")
                print()
            rc = 1
        else:
            print(f"  NEAR: none above {near}")

    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
