#!/usr/bin/env bash
# Build-script self-test -- Phase 1 exit condition.
#
# Never trust a build you have not seen fail.  A build that tests only
# [ -f out.pdf ] will "succeed" on a leftover artifact from an earlier run and
# ship a stale PDF.  Verified reproduction in the source project: a fatally
# broken source printed "wrote .../main.pdf (1 pages)" while main.pdf still
# contained the previous build's text.
#
# Breaks main.tex on purpose, builds, and asserts the build FAILS and ships
# nothing stale.  Restores main.tex unconditionally.
#
# Usage: build_selftest.sh [<paper-dir>]
set -uo pipefail
d="${1:-.}"
cd "$d" || exit 1

command -v pdflatex >/dev/null 2>&1 || {
  echo "SKIP: no TeX distribution here -- Phase 1 exit condition NOT verified"; exit 3; }

cleanup () { [ -f main.tex.selftest.bak ] && mv -f main.tex.selftest.bak main.tex; }
trap cleanup EXIT INT TERM

cp main.tex main.tex.selftest.bak
before=$( [ -f main.pdf ] && pdftotext main.pdf - 2>/dev/null | head -2 || echo "")

printf '\n\\begin{nosuchenv}x\\end{nosuchenv}\n' >> main.tex
make main >/dev/null 2>&1
rc=$?
echo "broken-source build exit=$rc  (MUST be non-zero)"

fail=0
[ "$rc" -eq 0 ] && { echo "FAIL: build reported success on a fatally broken source"; fail=1; }
after=$( [ -f main.pdf ] && pdftotext main.pdf - 2>/dev/null | head -2 || echo "")
if [ -n "$before" ] && [ "$before" = "$after" ] && [ "$rc" -eq 0 ]; then
  echo "FAIL: main.pdf still contains the previous build's text -- stale artifact shipped"
  fail=1
fi
exit $fail
