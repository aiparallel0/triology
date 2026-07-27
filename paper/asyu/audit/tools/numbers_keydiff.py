#!/usr/bin/env python3
"""Result key-set diff -- proves no result was lost.

Catches a result silently dropped while restructuring or cutting for space.
Run before and after any edit that moves numbers between captions and body:

    git show HEAD:paper/asyu/main.tex > /tmp/before.tex
    numbers_keydiff.py /tmp/before.tex paper/asyu/main.tex

"REMOVED entirely: NONE" is mandatory.  Occurrence-count changes are
acceptable ONLY when you can name the duplicate you removed and confirm the
value still appears somewhere -- e.g. a caption that repeated a number already
in its own table.  The check does not clear you; it tells you what to justify.

This paper carries its results as \\-macros fed by numbers_*.tex rather than
\\PH{} slots, so both are counted.
"""
import collections
import re
import sys

# Macros defined from the results pipeline: \newcommand{\poolN}{1019} etc.
DEF = re.compile(r'\\newcommand\{\\([A-Za-z]+)\}')


def keys(path, defined):
    txt = re.sub(r'(?<!\\)%.*', '', open(path, encoding='utf8').read())
    c = collections.Counter(re.findall(r'\\PH\{([^}]+)\}', txt))
    for name in defined:
        # uses of the macro, not its definition
        n = len(re.findall(r'\\' + name + r'(?![A-Za-z])', txt)) - 1
        if n > 0:
            c[name] = n
    return c


def defined_macros(path):
    txt = open(path, encoding='utf8').read()
    return set(DEF.findall(txt))


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    before, after = argv[1], argv[2]
    defined = defined_macros(before) | defined_macros(after)
    a, b = keys(before, defined), keys(after, defined)
    if not a and not b:
        print("NO RESULT KEYS FOUND in either file -- wrong input? check did "
              "not run")
        return 2
    removed = [k for k in a if k not in b]
    added = [k for k in b if k not in a]
    print("REMOVED entirely:", removed or "NONE")
    print("ADDED:           ", added or "NONE")
    for k in sorted(set(a) | set(b)):
        if a[k] != b[k]:
            print(f"  {k}: {a[k]} -> {b[k]} occurrences")
    return 1 if removed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
