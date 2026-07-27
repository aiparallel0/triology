#!/usr/bin/env bash
# Placeholder-leak check -- the silent content killer.
#
# Two unfilled \PH{} on one line once deleted a figure, a table, a statistical
# result and the section numbering from a PDF that still compiled to the
# correct page count.  \PH{cam_npcr1px} puts an underscore into text mode;
# under -interaction=nonstopmode LaTeX "recovers" by consuming tokens, and the
# recovery swallows the following floats.  Nothing looks missing on the page:
# the page just ends earlier and later material moves up.
#
# Any output at all is a defect.  Zero output is the only pass.
#
# Usage: placeholder_leak.sh <main.tex> [<main.pdf>]
set -uo pipefail
tex="${1:?usage: placeholder_leak.sh <main.tex> [<main.pdf>]}"
pdf="${2:-}"
fail=0

# Strip LaTeX comments first, keeping line numbers.  A \PH{} inside a comment
# is inert, and counting it is a false positive -- which this check produced on
# its first run, against a comment that explains \PH{}.  A check that cries
# wolf gets switched off, and then it is not a check.
src=$(mktemp); trap 'rm -f "$src"' EXIT
sed 's/\(^\|[^\\]\)%.*/\1/' "$tex" > "$src"

n=$(grep -c '\\PH{' "$src" || true)
echo "unsubstituted \\PH{} in $tex: $n"
[ "$n" -gt 0 ] && { grep -n '\\PH{' "$src" | sed 's/^/  /'; fail=1; }

# The fill script's miss-marker, and any default that was never overridden by
# a numbers_*.tex file.
if grep -nE '\[\?[a-z_0-9]+\]' "$src" >/dev/null 2>&1; then
  echo "miss-markers:"; grep -nE '\[\?[a-z_0-9]+\]' "$src" | sed 's/^/  /'; fail=1
fi
if grep -nE '\\newcommand\{\\[A-Za-z]+\}\{(NA|PENDING|TODO|TBD|XXX)\}' "$tex" >/dev/null 2>&1; then
  echo "macro defaults that must be overridden by a numbers_*.tex before shipping:"
  grep -nE '\\newcommand\{\\[A-Za-z]+\}\{(NA|PENDING|TODO|TBD|XXX)\}' "$tex" | sed 's/^/  /'
  echo "  (defaults are fine in source; the PDF arm below is what must be clean)"
fi

# A placeholder can survive as *visible text*, so also check the rendered PDF.
# The [0-9]e-0[0-9] arm catches Python scientific notation leaking into prose
# (4e-06), which should typeset as $4\times10^{-6}$.
if [ -n "$pdf" ] && [ -f "$pdf" ] && command -v pdftotext >/dev/null 2>&1; then
  hits=$(pdftotext "$pdf" - | grep -oE "\[\?[a-z_0-9]+\]|PH\{[a-z_]+\}|[0-9]e-0[0-9]|\bNA\b|\bPENDING\b|\bTODO\b" | sort -u || true)
  if [ -n "$hits" ]; then
    echo "leaked into the rendered PDF:"; echo "$hits" | sed 's/^/  /'; fail=1
  else
    echo "rendered PDF: clean"
  fi
else
  echo "rendered PDF: NOT CHECKED (need a built $pdf and pdftotext)"
fi

exit $fail
