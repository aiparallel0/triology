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

if ! command -v pdftotext >/dev/null 2>&1; then
  echo "SKIP: pdftotext not installed (poppler-utils) -- caption format NOT verified"
  exit 3
fi
if [ ! -f "$pdf" ]; then
  echo "SKIP: $pdf not built -- caption format NOT verified"
  exit 3
fi

out=$(pdftotext "$pdf" - | grep -oE "Fig\. [0-9]+[.:]|TABLE [IVX]+:?" | sort -u)
echo "$out"
if echo "$out" | grep -q ':'; then
  echo "FAIL: colon in a caption label -- the class's \\@makecaption has been overridden"
  exit 1
fi
[ -z "$out" ] && { echo "FAIL: no captions found at all -- wrong PDF?"; exit 2; }
echo "OK: no colons; labels follow IEEEtran.cls"
