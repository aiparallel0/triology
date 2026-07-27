#!/usr/bin/env python3
"""Static structure check -- brace, environment and \\if...\\fi balance.

Not a substitute for compiling.  It is what you run when you cannot compile,
so that the things a compiler would catch instantly do not survive to the one
machine that has a TeX distribution.  It catches the mechanical errors an edit
introduces: an unclosed group, a \\begin without its \\end, a \\newif whose
\\fi went missing.

Exit 0 clean, 1 on any imbalance, 2 if the file yielded nothing to check.

Usage: tex_structure.py <file.tex> [<file.tex> ...]
"""
import re
import sys

VERB = re.compile(r'\\verb\*?(.)')
IF = re.compile(r'\\(if[a-zA-Z@]*|else|fi)(?![a-zA-Z@])')
ENV = re.compile(r'\\(begin|end)\{([^}]*)\}')


def strip(text):
    """Remove comments and \\verb spans; keep line count intact."""
    out = []
    for line in text.split('\n'):
        line = re.sub(r'(?<!\\)%.*', '', line)
        m = VERB.search(line)
        while m:
            d = re.escape(m.group(1))
            line = re.sub(r'\\verb\*?' + d + r'[^' + d + r']*' + d, 'VERB',
                          line, count=1)
            nxt = VERB.search(line)
            m = nxt if nxt and nxt.start() != m.start() else None
        out.append(line)
    return out


def check(path):
    lines = strip(open(path, encoding='utf8').read())
    if not any(l.strip() for l in lines):
        print(f"{path}: EMPTY after comment stripping -- nothing checked")
        return 2

    bad = []

    # 1. braces, ignoring \{ \} \verb and catcode games
    depth, opened = 0, []
    for n, line in enumerate(lines, 1):
        for i, ch in enumerate(line):
            if ch in '{}' and (i == 0 or line[i - 1] != '\\'):
                if ch == '{':
                    depth += 1
                    opened.append(n)
                else:
                    depth -= 1
                    if opened:
                        opened.pop()
                    if depth < 0:
                        bad.append(f"  line {n}: closing brace with no opener")
                        depth = 0
    if depth:
        bad.append(f"  {depth} unclosed brace(s); oldest opened near line "
                   f"{opened[0] if opened else '?'}")

    # 2. environments
    stack = []
    for n, line in enumerate(lines, 1):
        for kind, name in ENV.findall(line):
            if kind == 'begin':
                stack.append((name, n))
            else:
                if not stack:
                    bad.append(f"  line {n}: \\end{{{name}}} with no \\begin")
                elif stack[-1][0] != name:
                    o, on = stack.pop()
                    bad.append(f"  line {n}: \\end{{{name}}} closes "
                               f"\\begin{{{o}}} from line {on}")
                else:
                    stack.pop()
    for name, n in stack:
        bad.append(f"  \\begin{{{name}}} at line {n} never closed")

    # 3. \if ... \fi  (\newif-declared conditionals included)
    #    \newif{\iffoo} DECLARES rather than opens, so skip those lines.
    d, first = 0, None
    for n, line in enumerate(lines, 1):
        if '\\newif' in line:
            continue
        for tok in IF.findall(line):
            if tok.startswith('if'):
                d += 1
                if first is None:
                    first = n
            elif tok == 'fi':
                d -= 1
                if d == 0:
                    first = None
                if d < 0:
                    bad.append(f"  line {n}: \\fi with no \\if")
                    d = 0
    if d:
        bad.append(f"  {d} unclosed \\if...\\fi; oldest near line {first}")

    if bad:
        print(f"{path}: STRUCTURE ERRORS")
        print('\n'.join(bad))
        return 1
    print(f"{path}: braces, environments and \\if/\\fi balanced")
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for p in argv[1:]:
        rc = max(rc, check(p))
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
