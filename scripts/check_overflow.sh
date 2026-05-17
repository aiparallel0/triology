#!/usr/bin/env bash
# Root-cause guard against column overflow / figure-table misalignment.
# Builds the paper and FAILS if LaTeX reports any Overfull \hbox.
# microtype + emergencystretch (in main.tex) prevent the common cases;
# this catches any that still slip through (wide tikz/tabular, unbreakable
# \texttt paths) so a regression cannot reach a PDF unnoticed.
#
# Usage: scripts/check_overflow.sh            (checks paper/asyu/main.tex)
#        scripts/check_overflow.sh <file.tex>
set -euo pipefail
cd "$(dirname "$0")/../paper/asyu"
TEX="${1:-main.tex}"
BASE="${TEX%.tex}"
latexmk -pdf -interaction=nonstopmode "$TEX" >/dev/null 2>&1 || true
LOG="${BASE}.log"
[ -f "$LOG" ] || { echo "FAIL: $LOG not produced (build broken)"; exit 2; }
N=$(grep -c 'Overfull \\hbox' "$LOG" || true)
if [ "$N" -ne 0 ]; then
  echo "FAIL: $N Overfull \\hbox in $LOG -- fix before committing:"
  grep -n 'Overfull \\hbox' "$LOG" | head -20
  exit 1
fi
echo "OK: 0 Overfull \\hbox in $BASE ($(grep -c 'Undefined control sequence' "$LOG" || echo 0) undefined ctrl seqs)"
