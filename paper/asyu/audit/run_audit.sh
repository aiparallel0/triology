#!/usr/bin/env bash
# Run the whole audit kit against the ASYU sigma-verifier paper.
#
#   bash audit/run_audit.sh            # from paper/asyu/
#
# Every check states what it catches and how to read it in its own header.
# Checks that need a rendered PDF or a TeX distribution report SKIP rather than
# silently passing: a check whose "could not run" state is indistinguishable
# from "nothing wrong" is worse than no check.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
d="$(cd "$here/.." && pwd)"
T="$here/tools"
PAGE_LIMIT="${PAGE_LIMIT:-6}"

pass=0; failed=0; skipped=0
run () {  # run <name> <command...>
  echo
  echo "──────────────────────────────────────────────────────────────────────"
  echo "▶ $1"
  echo "──────────────────────────────────────────────────────────────────────"
  shift
  "$@"; rc=$?
  case $rc in
    0) echo "  → PASS"; pass=$((pass+1));;
    3) echo "  → SKIP (not verifiable in this environment)"; skipped=$((skipped+1));;
    *) echo "  → FAIL (exit $rc)"; failed=$((failed+1));;
  esac
}

cd "$d" || exit 1

run "0a. classifier self-test (the checker must reproduce the defect)" \
    bash "$T/selftest_float_refs.sh"
run "0b. LaTeX structure: braces, environments, \\if...\\fi" \
    python3 "$T/tex_structure.py" main.tex
run "0c. change marks: is any \\chgi span too long to break?" \
    python3 "$T/chg_span.py" main.tex
run "1. float references: cited, or actually discussed? (committee item 3)" \
    python3 "$T/float_refs.py" main.tex
run "2. placeholder leak (the silent content killer)" \
    bash "$T/placeholder_leak.sh" main.tex main.pdf
run "4. caption format on the RENDERED pdf (committee item 2)" \
    bash "$T/caption_format.sh" main.pdf
run "5. build gate: page count / overfull / undefined" \
    bash "$T/gate.sh" "$d" "$PAGE_LIMIT" main
run "6. self-contained package (Phase 6 exit condition)" \
    bash "$T/selfcontained.sh" "$d"
run "7. heading Title Case (reviewer rule 6)" \
    python3 "$T/headings_titlecase.py" main.tex
run "7b. ASYU editor e-mail: the four requested items" \
    python3 "$T/editor_items.py" main.tex
run "8. numbers consistency (READ THIS ONE YOURSELF)" \
    bash "$T/numbers_consistency.sh" main.tex
run "9. disclosure verification (READ THIS ONE YOURSELF)" \
    bash "$T/disclosure_check.sh" "$d"

echo
echo "══════════════════════════════════════════════════════════════════════"
echo "  pass=$pass  fail=$failed  skip=$skipped   (page limit $PAGE_LIMIT)"
echo "  Checks 3 (key-set diff) and the build self-test are run by hand:"
echo "    git show HEAD:paper/asyu/main.tex > /tmp/before.tex"
echo "    python3 audit/tools/numbers_keydiff.py /tmp/before.tex main.tex"
echo "    bash audit/tools/build_selftest.sh ."
echo "  SKIP is not PASS.  A skipped check is an unverified claim -- log it in"
echo "  audit/UNVERIFIED.md."
echo "══════════════════════════════════════════════════════════════════════"
exit $(( failed > 0 ))
