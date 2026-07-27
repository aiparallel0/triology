#!/usr/bin/env bash
# Regression test for float_refs.py.
#
# "The checker must reproduce the historical defect, or it is not measuring
# anything."  Three cases, mirroring the three bugs the classifier had:
#   1. an all-parenthetical paper must FAIL and list every float
#   2. a paper with proper subject-position references must PASS
#   3. an empty / wrong input must exit 2, never 0
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
tool="$here/float_refs.py"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail=0

check () {  # check <name> <expected-exit> <file>
  python3 "$tool" "$3" >"$tmp/out" 2>&1
  got=$?
  if [ "$got" -eq "$2" ]; then
    echo "PASS  $1 (exit $got)"
  else
    echo "FAIL  $1 (exit $got, wanted $2)"; sed 's/^/      /' "$tmp/out"; fail=1
  fi
}

# 1. the historical defect: cited everywhere, discussed nowhere
cat >"$tmp/parenthetical.tex" <<'EOF'
\begin{figure}\caption{x}\label{fig:a}\end{figure}
\begin{table}\caption{y}\label{tab:b}\end{table}
The rate falls to 1.1\% (Fig.~\ref{fig:a}, left), and the pooled cells
(Table~\ref{tab:b}) agree with the per-corpus split.
EOF
check "all-parenthetical must fail" 1 "$tmp/parenthetical.tex"
grep -q "fig:a" "$tmp/out" && grep -q "tab:b" "$tmp/out" \
  || { echo "FAIL  all-parenthetical did not list both floats"; fail=1; }

# 2. the fixed form, including the two shapes that must NOT false-fail:
#    a sentence-initial adverbial, and a conjoined clause after \end{table}
cat >"$tmp/subject.tex" <<'EOF'
\begin{figure}\caption{x}\label{fig:a}\end{figure}
\begin{table}\caption{y}\label{tab:b}\end{table}
\subsection{Reproduction}
Finally, Fig.~\ref{fig:a} shows the per-corpus split.
\begin{table}\end{table}
Table~\ref{tab:b} reports the pooled cells.
EOF
check "subject-position must pass" 0 "$tmp/subject.tex"

# 3. zero floats must not score a perfect pass
: >"$tmp/empty.tex"
check "empty input must exit 2" 2 "$tmp/empty.tex"

exit $fail
