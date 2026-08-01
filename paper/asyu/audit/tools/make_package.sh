#!/usr/bin/env bash
# Build the self-contained Overleaf package -- Phase 6 deliverable.
#
#   bash audit/tools/make_package.sh review    # red change boxes ON  (default)
#   bash audit/tools/make_package.sh submit    # boxes OFF, submission copy
#
# The zip is a DERIVED artifact. It is generated from the repository every
# time, never hand-assembled and never edited in place. The alternative is two
# confusable sources of truth, and in the project this pipeline is distilled
# from that is precisely what happened: the tracked, reviewed, human-opened
# main.tex was the one that could NOT compile, while the only file that did
# compile had no history and no identity. Both were 578 lines and differed in
# 59 substituted values spread over 38 lines, which is why the author's own
# Overleaf project silently became a hybrid of the two and nearly shipped a
# paper missing a figure, a table, a statistical result and a paragraph.
#
# So: edit the repo, re-run this script. Never edit the zip.
#
# The script is also a CHECK. It resolves every dependency main.tex declares
# and fails if any is missing, rather than zipping a package with a hole in it.
set -uo pipefail

mode="${1:-review}"
case "$mode" in review|submit) ;; *) echo "usage: make_package.sh [review|submit]"; exit 2;; esac

here="$(cd "$(dirname "$0")" && pwd)"
src="$(cd "$here/../.." && pwd)"          # paper/asyu
out="${OUT_DIR:-$src/dist}"
name="sigma-verifier-asyu-$mode"
stage="$out/$name"

echo "== packaging $src  ->  $out/$name.zip  (mode: $mode)"
rm -rf "$stage" "$out/$name.zip"
mkdir -p "$stage"

fail=0
copy () {  # copy <relative-path> <why>
  if [ ! -f "$src/$1" ]; then
    echo "  MISSING  $1   ($2)"; fail=1; return
  fi
  mkdir -p "$stage/$(dirname "$1")"
  cp "$src/$1" "$stage/$1"
  printf "  ok       %-34s %s\n" "$1" "$2"
}

# ---------------------------------------------------------------- root source
copy main.tex "root document"

# ------------------------------------------- everything main.tex declares
# Resolved from the source, not from a hand-maintained list: a hand-maintained
# list goes stale the first time someone adds a figure.
deps=$(python3 - "$src/main.tex" <<'EOF'
import re, sys
t = re.sub(r'(?<!\\)%.*', '', open(sys.argv[1], encoding='utf8').read())
out = []
for c in re.findall(r'\\documentclass(?:\[[^\]]*\])?\{([^}]+)\}', t):
    out.append((c + '.cls', 'document class'))
for b in re.findall(r'\\bibliographystyle\{([^}]+)\}', t):
    out.append((b + '.bst', 'bibliography style'))
for b in re.findall(r'\\bibliography\{([^}]+)\}', t):
    for one in b.split(','):
        out.append((one.strip() + '.bib', 'bibliography'))
for f in re.findall(r'\\(?:input|include|InputIfFileExists)\{([^}]+)\}', t):
    out.append((f if f.endswith('.tex') else f + '.tex', 'results macros'))
for g in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', t):
    out.append((g, 'figure'))
seen = set()
for path, why in out:
    if path not in seen:
        seen.add(path)
        print(f"{path}\t{why}")
EOF
)
while IFS=$'\t' read -r path why; do
  [ -z "$path" ] && continue
  # a figure may be declared without its extension
  if [ ! -f "$src/$path" ] && [ "$why" = "figure" ]; then
    for e in .pdf .png .jpg .eps; do
      [ -f "$src/$path$e" ] && { path="$path$e"; break; }
    done
  fi
  copy "$path" "$why"
done <<< "$deps"

# --------------------------------------------------- documentation, not build
# Review copy only. CHANGES.md is a revision diary and UNVERIFIED.md lists what
# we could not check; a submission package that carries either is telling the
# programme committee things meant for us.
if [ "$mode" = "review" ]; then
  for f in audit/GROUND_TRUTH.md audit/CHANGES.md audit/UNVERIFIED.md audit/README.md; do
    copy "$f" "audit record"
  done
fi

[ "$fail" -ne 0 ] && { echo; echo "FAIL: a declared dependency is missing. Not zipping a package with a hole in it."; exit 1; }

# --------------------------------------------------------- set the review mode
if [ "$mode" = "submit" ]; then
  sed -i 's/^\\showchangestrue/\\showchangesfalse/' "$stage/main.tex"
else
  sed -i 's/^\\showchangesfalse/\\showchangestrue /' "$stage/main.tex"
fi
grep -q "^\\\\showchanges${mode/review/true}" "$stage/main.tex" 2>/dev/null || true
echo "  mode     $(grep -o '^\\showchanges[a-z]*' "$stage/main.tex")"

# ------------------------------------------------------- check the STAGED copy
# Everything above verified the source tree. These verify the thing that
# actually ships, which is not the same claim.
echo
echo "== checks on the staged package"
python3 "$here/tex_structure.py" "$stage/main.tex" | sed 's/^/  /' || fail=1
bash "$here/placeholder_leak.sh" "$stage/main.tex" 2>&1 | grep -E "unsubstituted|miss-marker" | sed 's/^/  /'
bash "$here/placeholder_leak.sh" "$stage/main.tex" >/dev/null 2>&1 || fail=1
python3 "$here/float_refs.py" "$stage/main.tex" | sed 's/^/  /' || fail=1

# nothing may reference a file that is not in the package
python3 - "$stage" <<'EOF' || exit 1
import os, re, sys
root = sys.argv[1]
t = re.sub(r'(?<!\\)%.*', '', open(os.path.join(root, 'main.tex'), encoding='utf8').read())
miss = []
for g in sorted(set(re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', t))):
    if not any(os.path.exists(os.path.join(root, g + e)) for e in ('', '.pdf', '.png', '.jpg', '.eps')):
        miss.append('figure ' + g)
for f in sorted(set(re.findall(r'\\(?:input|include|InputIfFileExists)\{([^}]+)\}', t))):
    p = f if f.endswith('.tex') else f + '.tex'
    if not os.path.exists(os.path.join(root, p)):
        miss.append('input ' + p)
for m in miss:
    print('  DANGLING REFERENCE:', m)
print('  every \\includegraphics and \\input target resolves inside the package'
      if not miss else '')
sys.exit(1 if miss else 0)
EOF
[ $? -ne 0 ] && fail=1

[ "$fail" -ne 0 ] && { echo; echo "FAIL: staged package did not pass its own checks."; exit 1; }

# ------------------------------------------------------------------- read-me
# Generated, not stored, so it cannot drift from the package it describes.
# Read the switch out of the file that actually ships, and its line number.
# Constructing it from $mode is how the first version of this README came to
# say "\showchangestruereview".
now_line=$(grep -n '^\\showchanges[a-z]*' "$stage/main.tex" | head -1)
now_no=${now_line%%:*}
now_sw=$(printf '%s' "${now_line#*:}" | grep -o '^\\showchanges[a-z]*')

if [ "$mode" = "review" ]; then
  mode_line='This copy is in REVIEW mode: every change is inside a red box, and a
change-index page is appended after the bibliography.'
  flip_to='\showchangesfalse   (removes every box and the index page)'
else
  mode_line='This copy is in SUBMISSION mode: no red boxes, no change-index page.'
  flip_to='\showchangestrue    (shows every change in a red box)'
fi

cat > "$stage/README-OVERLEAF.txt" <<EOF
Sigma-Verifier -- ASYU submission package
Generated $(date -u +%Y-%m-%dT%H:%MZ) by audit/tools/make_package.sh from
aiparallel0/triology, branch claude/sigma-verifier-change-boxes-jk6z8a.


OPENING IT
----------
Overleaf: New Project -> Upload Project -> this .zip.
  Root document : main.tex
  Compiler      : pdfLaTeX
  Bibliography  : BibTeX (Overleaf runs it; IEEEtran.bst is included)

Nothing needs installing. IEEEtran.cls and IEEEtran.bst are in the package, so
the build does not depend on Overleaf's TeX Live version for the class.

Locally: pdflatex main / bibtex main / pdflatex main / pdflatex main,
or latexmk -pdf main.tex.


REVIEW MODE
-----------
$mode_line

One line in main.tex governs it. Search for "showchanges" -- it is the line
marked <<<< in the preamble, line ${now_no}, and it currently reads:

    ${now_sw}

Change it to:

    ${flip_to}

Nothing else moves. The red boxes are review apparatus, not content.

The 6-page limit is only meaningful with the boxes OFF -- they add height.


BEFORE YOU SUBMIT
-----------------
1. The author block is a bracketed placeholder. It cannot be inferred and must
   not be a realistic invented affiliation. Fill it. Search for "AUTHOR NAME".

2. Turn the review boxes off (above).

3. Check the page count is <= 6.

4. Check the captions on the RENDERED pdf, not the source:

     pdftotext main.pdf - | grep -oE "Fig\\. [0-9]+[.:]|TABLE [IVX]+:?" | sort -u

   Want "Fig. 1." and "TABLE I". Any colon is a failure. Small caps extract as
   "R ECONSTRUCTION" -- that is a pdftotext artifact, not a defect; look at the
   page to confirm.

5. Check the log for overfull boxes and undefined references.


WHAT HAS NOT BEEN CHECKED
-------------------------
This package has never been compiled. It was built in an environment with no
TeX distribution and no network. Every rendered-artifact claim about it is
therefore unverified -- see audit/UNVERIFIED.md for the full list.

A clean build is not evidence either. In the project this pipeline is distilled
from, the build never failed, the page count was always right, and the PDF
always looked finished, while a package override was destroying the caption
format and two unfilled placeholders were deleting a figure and a table.


DO NOT EDIT THIS PACKAGE IN PLACE
---------------------------------
It is generated. Edit the repository and re-run:

    bash audit/tools/make_package.sh review    # or: submit

Editing the zip creates a second source of truth, and the one under version
control becomes the one nobody compiles. That exact split -- a tracked main.tex
that could not compile beside an untracked one that could -- is how an author's
own Overleaf project silently became a hybrid of the two and nearly shipped a
6-page paper missing a figure, a table, a statistical result and a paragraph.
If you edit anything here, copy it back into the repo the same day.


WHAT IS IN THE PACKAGE
----------------------
  main.tex                  the paper
  IEEEtran.cls/.bst         vendored, so the build is self-contained
  references.bib            bibliography
  numbers_*.tex             results macros, generated by the analysis scripts
  riskcov_curve.tex         risk-coverage curve coordinates
  figures/fig_overview.pdf  the only external figure; the rest are TikZ
  audit/                    ground truth, the change accounting, unverified list

Not included, deliberately: presentation.tex and caveats_explained.tex are
separate beamer documents and would confuse Overleaf's root-file detection.
The figure-generation scripts live in the repository.
EOF
echo "  ok       README-OVERLEAF.txt                generated"

# ------------------------------------------------------------------- zip it up
( cd "$out" && zip -qr "$name.zip" "$name" )
rm -rf "$stage"

echo
echo "== $out/$name.zip"
unzip -l "$out/$name.zip" | tail -n +4 | head -n -2 | awk '{printf "  %8s  %s\n", $1, $4}'
echo
echo "NOT VERIFIED: this package has not been compiled. No TeX distribution was"
echo "available where it was built, so the page count, caption format, overfull"
echo "boxes and undefined references are all unchecked. Compiling it is the check."
