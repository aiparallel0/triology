#!/usr/bin/env python3
"""ASYU editor e-mail -- the four requested items, checked in the source.

  1. Abstract and Keywords at line spacing 1; after the Abstract, 0.95.
  2. 10 nk between Abstract and Keywords.
  3. 6 nk after every paragraph.
  4. A period after the table label: "TABLE I."

Source-level only. Items 1-3 are vertical metrics and item 4 is a caption
label: NONE of them is proven here. They are proven on the rendered PDF, and
the last lines tell you how.

Three of the six checks are "X appears between Y and Z", which is inherently
multi-line. The first version of this used `grep -E` with \\x01 as a flattened
newline; GNU grep -E does not interpret \\x01, so it reported three false
MISSes against a file that was correct. Hence Python.

Usage: editor_items.py [<main.tex>]
"""
import os
import re
import sys

CHECKS = [
    ("1a", "Abstract at line spacing 1",
     r'\\begin\{abstract\}(?:[^\n]*\n){0,4}[^\n]*\\linespread\{1\}'),
    ("1b", "Keywords at line spacing 1",
     r'\\begin\{IEEEkeywords\}(?:[^\n]*\n){0,4}[^\n]*\\linespread\{1\}'),
    ("1c", "body after the Abstract at 0.95",
     r'\\linespread\{0\.95\}\\selectfont'),
    ("2 ", "10 nk between Abstract and Keywords",
     r'\\end\{abstract\}(?:[^\n]*\n){0,8}[^\n]*\\vspace\{10pt\}'),
    ("3 ", "6 nk after every paragraph",
     r'\\setlength\{\\parskip\}\{6pt'),
    ("4 ", "period after the table label (TABLE I.)",
     r'\\def\\fnum@table\{\\tablename\\nobreakspace\\thetable\.\}'),
]


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    tex = argv[1] if len(argv) > 1 else os.path.join(here, '..', '..', 'main.tex')
    if not os.path.exists(tex):
        print(f"no such file: {tex}")
        return 2
    raw = open(tex, encoding='utf8').read()
    src = re.sub(r'(?<!\\)%.*', '', raw)

    fail = 0
    print(f"ASYU editor items in {os.path.basename(tex)}:")
    for n, desc, pat in CHECKS:
        if re.search(pat, src):
            print(f"  ok    {n}  {desc}")
        else:
            print(f"  MISS  {n}  {desc}")
            fail = 1

    # Item 4 must NOT have been done with the caption package: it has no
    # IEEEtran support and replaces \@makecaption wholesale, which would put
    # colons on every figure caption and delete the small-caps table titles.
    if re.search(r'\\usepackage(?:\[[^\]]*\])?\{caption\}', src):
        print("  FAIL  4   \\usepackage{caption} is loaded -- it overrides")
        print("            IEEEtran's \\@makecaption. Item 4 must be done via")
        print("            \\fnum@table alone.")
        fail = 1

    # The review boxes add height; the page limit is only meaningful without.
    if re.search(r'^\\showchangestrue', src, re.M):
        print()
        print("  NOTE: review mode is ON. The change-index page alone is +1 page.")
        print("        Run 'bash audit/tools/showchanges.sh off' before counting.")

    print()
    print("  Verify on the RENDERED pdf -- none of the above proves the output:")
    print(r"    pdftotext main.pdf - | grep -oE 'TABLE [IVX]+\.?' | sort -u")
    print("      want 'TABLE I.' with the period, on every table")
    print("    pdfinfo main.pdf | grep Pages          # must be 6")
    return fail


if __name__ == '__main__':
    sys.exit(main(sys.argv))
