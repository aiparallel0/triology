#!/usr/bin/env bash
# Turn the removable red change boxes on or off.
#
# Every edit the venue-conformance pass made to main.tex is wrapped in \chgi,
# \chgcap or the chgblock environment.  All of them are governed by ONE line in
# the preamble.  This script flips that line, so "removable" is a command, not
# a manual search.
#
#   showchanges.sh on       -- red boxes visible, review copy
#   showchanges.sh off      -- boxes gone, submission copy
#   showchanges.sh status   -- which mode is main.tex in
#
# The page-limit gate is only meaningful in "off" mode: the boxes add height.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
tex="${TEX:-$here/../../main.tex}"
[ -f "$tex" ] || { echo "no such file: $tex"; exit 2; }

case "${1:-status}" in
  on)
    sed -i 's/^\\showchangesfalse/\\showchangestrue /' "$tex"
    sed -i 's/^\\showchangestrue *$/\\showchangestrue/' "$tex"
    ;;
  off)
    sed -i 's/^\\showchangestrue/\\showchangesfalse/' "$tex"
    ;;
  status) ;;
  *) echo "usage: showchanges.sh on|off|status"; exit 2;;
esac

if grep -q '^\\showchangestrue' "$tex"; then
  echo "review mode ON  -- red change boxes are visible in $(basename "$tex")"
  echo "  (do not submit this build; run 'showchanges.sh off' first)"
elif grep -q '^\\showchangesfalse' "$tex"; then
  echo "review mode OFF -- clean submission copy"
else
  echo "WARNING: no \\showchanges{true,false} line found in $tex"
  exit 1
fi
