#!/usr/bin/env bash
# Numbers-consistency check.
#
# Catches the same quantity stated two ways (a decrypt timing appeared as both
# 0.101 s and 0.037 s in one paper).
#
# READ IT MANUALLY.  The point is to *look* at repeated decimals and ask
# whether two of them are the same quantity disagreeing.  Automating the
# judgement is not possible; automating the enumeration is.
#
# Usage: numbers_consistency.sh <main.pdf|main.tex>
set -uo pipefail
f="${1:?usage: numbers_consistency.sh <main.pdf|main.tex>}"

if [ "${f##*.}" = "pdf" ]; then
  command -v pdftotext >/dev/null 2>&1 || {
    echo "SKIP: pdftotext not installed -- run against main.tex instead"; exit 3; }
  [ -f "$f" ] || { echo "SKIP: $f not built"; exit 3; }
  text=$(pdftotext "$f" -)
else
  text=$(sed 's/\(^\|[^\\]\)%.*/\1/' "$f")
fi

echo "== repeated decimals (count, value) =="
echo "$text" | grep -oE '[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn | head -30

echo
echo "== every value's source, for anything that should be unique =="
echo "   grep -rn '<value>' runs/*.json paper/asyu/numbers_*.tex paper/asyu/main.tex"
