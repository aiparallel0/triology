#!/usr/bin/env python3
"""ASYU editor e-mail -- the four requested items, checked in the source.

  1. Abstract and Keywords at line spacing 1.
  2. 10 nk between Abstract and Keywords.
  3. 6 nk after every paragraph.
  4. The table label. The editor asked for a period ("TABLE I."); the
     authors chose the IEEEtran default ("TABLE I") instead, so this
     now checks that the period is absent. See the CHECKS entry.

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

def check_ten_nk(src):
    """The gap must MEASURE 10pt, which is not the same as writing 10pt.

    \\parskip already contributes its own 6pt after the abstract, so a bare
    \\vspace{10pt} there produces 16pt and silently overshoots what the editor
    asked for. The correct form subtracts what \\parskip gives:

        \\vspace{\\dimexpr 10pt-\\parskip\\relax}

    This check pinned the literal \\vspace{10pt} for three revisions, so it was
    asserting the bug rather than the requirement.
    """
    import re as _re
    seg = src[src.find('\\end{abstract}'):]
    seg = seg[:seg.find('\\begin{IEEEkeywords}') + 1] or seg[:400]
    if _re.search(r'\\vspace\{\\dimexpr\s*10pt\s*-\s*\\parskip', seg):
        return True
    # A bare 10pt is only correct when \parskip contributes nothing.
    if _re.search(r'\\vspace\{10pt\}', seg):
        m = _re.search(r'\\setlength\{\\parskip\}\{([0-9.]+)pt', src)
        return not m or float(m.group(1)) == 0
    return False


def check_no_table_period(src):
    """True when \\fnum@table is left alone, so IEEEtran prints "TABLE I"."""
    import re as _re
    return not _re.search(r'\\def\\fnum@table', src)


def check_no_body_linespread(src):
    """True when the body is NOT overridden away from the class default."""
    import re as _re
    for m in _re.finditer(r'\\linespread\{([0-9.]+)\}', src):
        if abs(float(m.group(1)) - 1.0) > 1e-9:
            return False
    return True



CHECKS = [
    ("1a", "Abstract at line spacing 1",
     r'\\begin\{abstract\}(?:[^\n]*\n){0,4}[^\n]*\\linespread\{1\}'),
    ("1b", "Keywords at line spacing 1",
     r'\\begin\{IEEEkeywords\}(?:[^\n]*\n){0,4}[^\n]*\\linespread\{1\}'),
    # The editor asked for spacing 1 in the Abstract and Keywords. Nothing was
    # asked about the body, and an earlier revision set it to 0.95 to buy back
    # the page the review responses cost -- compressing the class to fit rather
    # than following it. This check REQUIRED that hack, so it encoded our own
    # decision as if the editor had made it. It now checks the opposite: that
    # the body is left at IEEEtran's leading.
    ("1c", "body left at the IEEEtran default (no linespread hack)",
     check_no_body_linespread),
    ("2 ", "10 nk between Abstract and Keywords (net of \\parskip)",
     check_ten_nk),
    ("3 ", "6 nk after every paragraph",
     r'\\setlength\{\\parskip\}\{6pt'),
    # Item 4 of the editor's e-mail asked for a period after the table label
    # ("Cizelge etiketlerinden sonra . (nokta) kullaniniz"), and this check
    # required the \fnum@table redefinition that produces it. The authors have
    # since decided to follow the IEEEtran template instead, which renders
    # "TABLE I" with no period. That is a deliberate override of the editor,
    # not a regression, so the check is inverted rather than deleted: it now
    # fails if the redefinition comes back, and the entry keeps the editor's
    # request on the record so nobody re-adds the period by accident.
    ("4 ", "table label left at the IEEEtran default (TABLE I, no period)",
     check_no_table_period),
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
        # An entry is either a regex to find or a predicate to satisfy. Item 1c
        # is the second kind: it asserts the ABSENCE of an override, and a
        # regex for "no match anywhere" is easy to get subtly wrong.
        ok = pat(src) if callable(pat) else bool(re.search(pat, src))
        if ok:
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
    print("      want 'TABLE I' at the IEEEtran default, no period")
    print("    pdfinfo main.pdf | grep Pages          # must be 6")
    return fail


if __name__ == '__main__':
    sys.exit(main(sys.argv))
