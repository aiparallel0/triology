#!/usr/bin/env bash
# Disclosure verification -- do not automate away.
#
# Catches claims about real-world actions asserted as fact, and claim strength
# that escalated across commits.  A progression like
#     "will be notified" -> "are notified" -> "we emailed ... received no response"
# is a fabrication in slow motion, even when no single commit looks like one.
# Only the human can confirm the underlying fact.
#
# For each hit, answer IN WRITING in audit/UNVERIFIED.md:
#     did this actually happen, and how do I know?
#
# Usage: disclosure_check.sh [<paper-dir>]
set -uo pipefail
d="${1:-.}"

echo "== assertions about real-world actions and verification =="
grep -rn -iE "we emailed|were notified|are notified|responsible.disclos|\
every citation|independently verified|we contacted|has been deployed|\
in production at|we confirmed with" "$d"/*.tex 2>/dev/null || echo "  (none)"

echo
echo "== unverified-by-construction claim shapes (hedge vs assertion) =="
grep -rn -iE "to our knowledge|the first|state.of.the.art|guarantees?|\
always|never fails|proven" "$d"/*.tex 2>/dev/null | head -20 || echo "  (none)"

echo
echo "== did the wording strengthen over time? =="
echo "  git log -p --follow -- $d/main.tex | grep -E '^[+-].*(notif|emailed|verified|first|guarantee)'"
