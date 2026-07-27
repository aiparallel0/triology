#!/usr/bin/env bash
# Build gate -- page count, overfull, undefined.
#
# Catches the three things that get a paper desk-rejected, plus a build that
# lies.  Wire the page limit in here so it can never be "discovered" late.
#
# Usage: gate.sh <paper-dir> [<page-limit>] [<jobname>]
set -euo pipefail
d="${1:-.}"; limit="${2:-6}"; job="${3:-main}"
log="$d/$job.log"; pdf="$d/$job.pdf"

if ! command -v pdflatex >/dev/null 2>&1 || ! command -v pdfinfo >/dev/null 2>&1; then
  echo "SKIP: no TeX distribution / poppler-utils here -- page count, overfull"
  echo "      boxes and undefined references are NOT verified."
  exit 3
fi
[ -f "$log" ] || { echo "FAIL: $log missing -- nothing was built"; exit 1; }
[ -f "$pdf" ] || { echo "FAIL: $pdf missing"; exit 1; }

# The page limit must be measured with the review boxes OFF.  Red change boxes
# add height; a review build over the limit is not a conformance failure, and a
# review build under it is not a pass.
if grep -q '^ *\\showchangestrue' "$d/main.tex" 2>/dev/null; then
  echo "NOTE: main.tex is in review mode (\\showchangestrue)."
  echo "      Run 'bash audit/tools/showchanges.sh off' before trusting pages=."
fi

# NOTE the `|| true` on every grep.  `grep -c` exits 1 when the count is 0,
# which under `set -e` aborts the script ON SUCCESS.  That is exactly the bug
# that made the source project's build script return exit 1 for a passing
# 6-page build and exit 0 for a failing 7-page one.  If you edit this file,
# test BOTH branches.
err=$(grep -c '^!'            "$log" || true)
ovf=$(grep -c 'Overfull'      "$log" || true)
und=$(grep -ci 'undefined'    "$log" || true)
pages=$(pdfinfo "$pdf" | awk '/^Pages:/{print $2}')

echo "pages=$pages/$limit errors=$err overfull=$ovf undefined=$und"
fail=0
[ "$pages" -gt "$limit" ] && { echo "FAIL: over page limit";      fail=1; }
[ "$err" -gt 0 ]          && { echo "FAIL: LaTeX errors";         fail=1; }
[ "$ovf" -gt 0 ]          && { echo "FAIL: overfull boxes";       fail=1; }
[ "$und" -gt 0 ]          && { echo "FAIL: undefined refs/cites"; fail=1; }
exit $fail
