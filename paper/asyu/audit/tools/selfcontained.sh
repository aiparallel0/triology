#!/usr/bin/env bash
# Clean-room compile -- Phase 6 exit condition.
#
# Catches a deliverable that only builds because of files sitting in your
# working tree.  Every \includegraphics target must be inside the package, and
# the package must compile from nothing.
#
# Usage: selfcontained.sh [<paper-dir>]
set -uo pipefail
d="${1:-.}"
cd "$d" || exit 1

echo "== \\includegraphics targets present? =="
python3 - <<'EOF'
import os, re, sys
t = open('main.tex', encoding='utf8').read()
t = re.sub(r'(?<!\\)%.*', '', t)
missing = 0
for g in sorted(set(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', t))):
    ok = any(os.path.exists(g + e) for e in ('', '.pdf', '.png', '.jpg', '.eps'))
    print(('  OK      ' if ok else '  MISSING ') + g)
    missing += 0 if ok else 1
sys.exit(1 if missing else 0)
EOF
gfx=$?
# NOTE: main.tex wraps \includegraphics so a missing figure renders a "figure
# pending" placeholder box instead of failing the build.  That keeps drafts
# reviewable and makes THIS check the only thing standing between you and a
# shipped paper with a grey box where Fig. 2 should be.  Do not ship on amber.

echo
echo "== clean-room compile =="
if ! command -v pdflatex >/dev/null 2>&1; then
  echo "  SKIP: no TeX distribution here -- Phase 6 exit condition NOT verified"
  exit $(( gfx ? 1 : 3 ))
fi
rm -f main.aux main.log main.bbl main.blg main.out main.pdf
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
bibtex main >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
pdflatex -interaction=nonstopmode main.tex >/dev/null 2>&1
echo "  pages=$(pdfinfo main.pdf | awk '/^Pages:/{print $2}')" \
     "errors=$(grep -c '^!' main.log || true)" \
     "overfull=$(grep -c Overfull main.log || true)" \
     "undefined=$(grep -ci undefined main.log || true)" \
     "placeholders=$(grep -c '\\PH{' main.tex || true)"
pdftotext main.pdf - | grep -oE "Fig\. [0-9]+\.|TABLE [IVX]+" | sort -u | tr '\n' ' '
echo
exit $gfx
