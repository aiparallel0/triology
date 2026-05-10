#!/usr/bin/env bash
# One-click: run all synthetic-data experiments end-to-end.
# Assumes onstart.sh has already cloned the repo and installed deps.
#
# Usage from the repo root (or pass --workdir):
#   bash vast/run.sh
#   bash vast/run.sh --n 2000 --seed 0

set -euo pipefail

# Resolve repo root: parent of this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PKG="$(basename "$REPO_DIR")"
PARENT="$(dirname "$REPO_DIR")"

N="${N:-500}"
SEED="${SEED:-0}"
while [ $# -gt 0 ]; do
  case "$1" in
    --n) N="$2"; shift 2;;
    --seed) SEED="$2"; shift 2;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

cd "$PARENT"
mkdir -p "$REPO_DIR/results"

echo "[run] S1 |T| distribution"
python3 -m "$PKG.scripts.s1_T_distribution" --corpus synthetic --n "$N"

echo "[run] S2 identity coverage"
python3 -m "$PKG.scripts.s2_I_coverage" --corpus synthetic --n "$N"

echo "[run] S3 confusion (synthetic)"
python3 -m "$PKG.scripts.s3_cord_confusion" --corpus synthetic --n "$N" --confusion_rate 0.08

echo "[run] S4 perturbation battery"
python3 -m "$PKG.scripts.s4_perturbation_battery" --corpus synthetic --n "$((N*4))"

echo "[run] S5 AAD overhead"
python3 -m "$PKG.scripts.s5_aad_overhead" --corpus synthetic --n "$N"

echo "[run] S6 expectation curve"
python3 -m "$PKG.scripts.s6_expectation" --corpus synthetic --n "$((N/2))"

echo "[run] all done — outputs under $REPO_DIR/results/"
