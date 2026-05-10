#!/usr/bin/env bash
# One-click: run all synthetic-data experiments end-to-end.
# Assumes onstart.sh has already cloned the repo and installed deps.
#
# Usage (run from repo root):
#   bash vast/run.sh
#   bash vast/run.sh --n 2000 --seed 0
#   bash vast/run.sh --adapter donut         # registers DONUT for S5/S7/S8
#
# Outputs land in <repo_root>/results/.

set -euo pipefail

# Resolve repo root: parent of this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PKG="$(basename "$REPO_DIR")"
PARENT="$(dirname "$REPO_DIR")"

N="${N:-500}"
SEED="${SEED:-0}"
ADAPTER=""
while [ $# -gt 0 ]; do
  case "$1" in
    --n)       N="$2"; shift 2;;
    --seed)    SEED="$2"; shift 2;;
    --adapter) ADAPTER="$2"; shift 2;;  # e.g. --adapter donut
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

run_script() {
  local mod="$1"; shift
  if [ -n "$ADAPTER" ]; then
    python3 -c "import $PKG.adapters.$ADAPTER, runpy, sys; sys.argv[0]='$mod'; runpy.run_module('$PKG.scripts.$mod', run_name='__main__')" -- "$@"
  else
    python3 -m "$PKG.scripts.$mod" "$@"
  fi
}

cd "$PARENT"
mkdir -p "$REPO_DIR/results"

echo "[run] S1 |T| distribution"
run_script "s1_T_distribution" --corpus synthetic --n "$N"

echo "[run] S2 identity coverage"
run_script "s2_I_coverage" --corpus synthetic --n "$N"

echo "[run] S3 confusion (synthetic)"
run_script "s3_cord_confusion" --corpus synthetic --n "$N" --confusion_rate 0.08

echo "[run] S4 perturbation battery"
run_script "s4_perturbation_battery" --corpus synthetic --n "$((N*4))"

echo "[run] S5 AAD overhead"
run_script "s5_aad_overhead" --corpus synthetic --n "$N"

echo "[run] S6 expectation curve"
run_script "s6_expectation" --corpus synthetic --n "$((N/2))"

echo "[run] all done — outputs under $REPO_DIR/results/"
