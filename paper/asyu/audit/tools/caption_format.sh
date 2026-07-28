#!/usr/bin/env bash
# Caption-format check -- committee item 2 / reviewer rules 3 and 4.
#
# Runs on the RENDERED PDF because that is the only place a package override is
# visible.  The source said font=footnotesize for 91 commits and looked fine
# too; source inspection cannot see what \usepackage{caption} did to the
# class's \@makecaption.
#
# Want:  "Fig. 1."   and   "TABLE I"      ANY COLON IS A FAILURE.
#
# Small caps extract oddly from pdftotext (R ECONSTRUCTION ...).  That is an
# extraction artifact, not a defect -- confirm visually:
#   pdftoppm -r 110 -png -f 3 -l 3 main.pdf /tmp/page
#
# Usage: caption_format.sh <main.pdf>
set -uo pipefail
pdf="${1:?usage: caption_format.sh <main.pdf>}"
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT

if ! command -v pdftotext >/dev/null 2>&1; then
  echo "SKIP: pdftotext not installed (poppler-utils) -- caption format NOT verified"
  exit 3
fi
if [ ! -f "$pdf" ]; then
  echo "SKIP: $pdf not built -- caption format NOT verified"
  exit 3
fi

# Caption labels only, matched in Python.
#
# Two things defeated the shell version:
#  1. A colon after a figure reference in PROSE ("... headline of Fig. 2: they
#     differ ...") is not a caption defect, and the first version reported one.
#     Telling them apart needs lookahead, which grep -E does not have -- the
#     pattern silently matched nothing and the fallback masked it.
#  2. pdftotext puts a space before the period after a roman numeral
#     ("TABLE IV ."), so a naive "TABLE [IVX]+\." misses four tables out of five.
#     That is an extraction artifact, exactly like small caps rendering as
#     "R ECONSTRUCTION". Do not chase it in the source.
pdftotext "$pdf" - > "$tmp" 2>/dev/null
python3 - "$tmp" <<'EOF'
import re, sys
t = open(sys.argv[1], encoding='utf8', errors='replace').read()
fig = sorted(set(m.group(0).strip() for m in
                 re.finditer(r'Fig\. \d+ ?[.:](?=\s+[A-Z(])', t)))
tab = sorted(set(re.sub(r'\s+', ' ', m.group(0)).strip() for m in
                 re.finditer(r'TABLE [IVX]+ ?[.:]?', t)))
print('  figure labels:', ' '.join(fig) or 'NONE')
print('  table labels :', ' '.join(tab) or 'NONE')
bad = [x for x in fig + tab if x.rstrip().endswith(':')]
if bad:
    print('FAIL: colon in a caption label:', ' '.join(bad))
    print('      the class\'s \\@makecaption has been overridden -- look for')
    print('      \\usepackage{caption} in the preamble.')
    sys.exit(1)
if not fig and not tab:
    print('FAIL: no captions found at all -- wrong PDF?')
    sys.exit(2)
missing = [x for x in tab if not x.rstrip().endswith('.')]
if missing:
    print('FAIL: table label without the period the editor asked for:',
          ' '.join(missing))
    sys.exit(1)
print('OK: no colons; every table label carries its period')
EOF
