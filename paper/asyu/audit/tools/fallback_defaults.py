#!/usr/bin/env python3
"""Fallback-default check -- the quietest way to publish a wrong number.

A results macro is declared in the preamble with a default, then overridden by
a generated file:

    \\newcommand{\\ctrlLsigma}{0.060}
    \\InputIfFileExists{numbers_control.tex}{}{}   % defines it as 0.050

\\InputIfFileExists is designed not to fail. If the generated file is missing,
renamed, or simply not shipped in the package, the paper still compiles and
still typesets a number -- the stale default. It looks like a result, so
nothing downstream can tell it is not one. In this paper thirty of eighty-five
defaults disagreed with the value their generated file supplies.

Two rules, both checked here:

  1. Every generated file is \\input, not \\InputIfFileExists, so a miss is a
     build error rather than a silent substitution.
  2. Every default that a generated file overrides is "??" and not a plausible
     number, so if rule 1 is ever relaxed the failure is visible on the page.

Rule 2 matters more than it looks. A build that stops is annoying; a build that
prints 0.060 where the experiment produced 0.050 is a retraction.

Exit 0 when both hold, 1 when either is broken, 2 when no results macros were
found at all -- that means the file changed shape and the check did not run.

Usage: fallback_defaults.py <main.tex> [<dir-with-generated-files>]
"""
import glob
import os
import re
import sys

VALUELIKE = re.compile(r'-?[\d.,%]+|EARNED|NOT EARNED')


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    tex = argv[1]
    d = argv[2] if len(argv) > 2 else os.path.dirname(os.path.abspath(tex)) or '.'
    src = open(tex, encoding='utf8').read()
    head = src[:src.find('\\begin{document}')]

    generated = set()
    for f in glob.glob(os.path.join(d, 'numbers_*.tex')) + \
             glob.glob(os.path.join(d, 'riskcov_curve.tex')):
        body = open(f, encoding='utf8').read()
        generated |= {m.group(1) for m in
                      re.finditer(r'\\(?:re)?newcommand\{\\([a-zA-Z]+)\}', body)}

    defaults = {m.group(1): (m.group(2) or '') for m in
                re.finditer(r'\\newcommand\{\\([a-zA-Z]+)\}\{([^{}]*)\}', head)}
    if not defaults:
        print(f"{tex}: NO MACRO DEFAULTS FOUND -- file changed shape? "
              f"check did not run")
        return 2

    soft = re.findall(r'\\InputIfFileExists\{([^}]+)\}', head)
    plausible = sorted(k for k, v in defaults.items()
                       if k in generated and VALUELIKE.fullmatch(v))
    orphan = sorted(k for k, v in defaults.items()
                    if k not in generated and VALUELIKE.fullmatch(v))

    print(f"{tex}")
    print(f"  results macros: {len(generated)} generated, "
          f"{len(defaults)} declared")

    rc = 0
    if soft:
        print(f"  FAIL: {len(soft)} file(s) loaded with \\InputIfFileExists, "
              f"which cannot fail:")
        for f in soft[:8]:
            print(f"    {f}")
        print("        use \\input so a missing generated file stops the build")
        rc = 1
    else:
        print("  OK: every generated file is \\input (a miss is fatal)")

    if plausible:
        print(f"  FAIL: {len(plausible)} default(s) look like real numbers "
              f"but are overridden at load time:")
        for k in plausible[:8]:
            print(f"    \\{k} = {defaults[k]}")
        print("        set these to ?? so a load failure is visible on the page")
        rc = 1
    else:
        print("  OK: no overridden default is a plausible number")

    if orphan:
        print(f"  note: {len(orphan)} value-like default(s) that no generated "
              f"file overrides -- typed by hand, so check them yourself:")
        for k in orphan[:6]:
            print(f"    \\{k} = {defaults[k]}")

    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
