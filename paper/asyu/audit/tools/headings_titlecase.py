#!/usr/bin/env python3
"""Heading Title Case -- reviewer rule 6.

"Alt basliklardaki her kelimenin ilk harfi buyuk olmali (title case)."

Checks \\section as well as \\subsection: in the source project all subsections
were fixed while three section titles stayed sentence case.

Acronyms and deliberate lowercase (kNN, softmax, \\sigma) false-positive here.
Review the output; do not auto-apply it.
"""
import re
import sys

SMALL = {'a', 'an', 'the', 'and', 'or', 'but', 'nor', 'for', 'of', 'in', 'on',
         'at', 'to', 'by', 'vs', 'with', 'from', 'as', 'into', 'over', 'per'}

# Words that are legitimately lowercase in this paper's vocabulary.
ALLOW = {'softmax', 'sigma', 'kNN'}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    bad = []
    for path in argv[1:]:
        src = re.sub(r'(?<!\\)%.*', '', open(path, encoding='utf8').read())
        for kind, title in re.findall(r'\\(section|subsection)\{([^}]*)\}', src):
            flat = re.sub(r'\\[A-Za-z]+', ' ', title)      # drop \sigma etc.
            words = re.findall(r"[A-Za-z][A-Za-z'-]*", flat)
            for i, w in enumerate(words):
                if w in ALLOW:
                    continue
                if w.lower() in SMALL and i not in (0, len(words) - 1):
                    continue
                if w[0].islower():
                    bad.append((path, kind, title, w))
                    break
    for p, k, t, w in bad:
        print(f"{p}: \\{k}{{{t}}}  (lowercase: {w!r})")
    print("OK" if not bad else f"{len(bad)} heading(s) not Title Case")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
