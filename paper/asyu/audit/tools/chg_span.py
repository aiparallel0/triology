#!/usr/bin/env python3
"""Marking-macro span check -- catches a box used where it cannot break.

\\chgi is an \\fcolorbox. A box does not break across lines. Wrap one word in
it and you get a red frame; wrap three sentences in it and TeX sets them as a
single unbreakable horizontal box that runs past the column edge and prints on
top of the neighbouring column. In a two-column IEEE layout the result is text
overprinting the other column and the bibliography.

This is not hypothetical. Six spans in this paper were marked that way after
the reviewer responses were folded into existing paragraphs, and the compiled
PDF had five full-width blocks where the columns should have been. The header
comment in main.tex had warned about it since the first commit -- the warning
was there and the check was not, so the warning lost.

The rule:

    \\chgi{...}   a span that fits on ONE LINE: a word, a heading, a field
    \\chgt{...}   a span folded mid-paragraph: red text between markers,
                  breaks wherever the paragraph breaks
    chgblock      a whole paragraph or several

Exit 0 when every marked span uses the macro that can survive its own length,
1 when one cannot, 2 when the file contains no marks at all -- a file with no
marks is not a file with nothing marked.

Usage: chg_span.py <file.tex> [--limit 110]
"""
import sys

LIMIT = 110


def strip_comments(src):
    """Blank out comments, preserving offsets so line numbers stay true.

    The header comment in main.tex documents the macros by name, so a checker
    that reads comments counts "\\chgt{...}" from the documentation as a real
    3-character span. Same false positive the placeholder check had.
    """
    out = []
    for line in src.split('\n'):
        i = line.find('%')
        while i > 0 and line[i - 1] == '\\':
            i = line.find('%', i + 1)
        out.append(line if i < 0 else line[:i] + ' ' * (len(line) - i))
    return '\n'.join(out)


def spans(src, macro):
    """Yield (offset, argument) for each macro call, honouring nested braces."""
    out = []
    needle = '\\' + macro + '{'
    i = 0
    while True:
        j = src.find(needle, i)
        if j < 0:
            return out
        k = j + len(needle)
        depth = 1
        while k < len(src) and depth:
            if src[k] == '\\':
                k += 2
                continue
            depth += (src[k] == '{') - (src[k] == '}')
            k += 1
        out.append((j, src[j + len(needle):k - 1]))
        i = k


def line_of(src, off):
    return src.count('\n', 0, off) + 1


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    limit = LIMIT
    if '--limit' in argv:
        limit = int(argv[argv.index('--limit') + 1])
    if not args:
        print(__doc__)
        return 2

    rc = 0
    for path in args:
        raw = open(path, encoding='utf8').read()
        src = strip_comments(raw)
        inline = spans(src, 'chgi')
        breakable = spans(src, 'chgt')
        blocks = src.count('\\begin{chgblock}')

        if not inline and not breakable and not blocks:
            print(f"{path}: NO CHANGE MARKS AT ALL -- wrong file, or the "
                  f"marking was lost? check did not run")
            return 2

        print(f"{path}")
        print(f"  \\chgi {len(inline)}   \\chgt {len(breakable)}   "
              f"chgblock {blocks}")

        over = [(o, a) for o, a in inline if len(a) > limit]
        if over:
            print(f"  FAIL: {len(over)} \\chgi span(s) longer than {limit} "
                  f"characters. \\chgi is an \\fcolorbox and cannot break --")
            print(f"        these will run past the column edge and overprint "
                  f"the next column. Use \\chgt.")
            for o, a in over[:8]:
                print(f"    L{line_of(src, o)}  {len(a):>5} chars  "
                      f"{' '.join(a.split())[:64]}")
            rc = 1
        else:
            print(f"  OK: every \\chgi span fits on a line (longest "
                  f"{max((len(a) for _, a in inline), default=0)} chars)")

        # The reverse mistake: \chgt on a span short enough to deserve a box.
        # Not a failure -- a box reads better when it fits -- but worth saying.
        small = [a for _, a in breakable if len(a) < 40]
        if small:
            print(f"  note: {len(small)} \\chgt span(s) under 40 chars would "
                  f"render better as \\chgi (a visible box)")

    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
