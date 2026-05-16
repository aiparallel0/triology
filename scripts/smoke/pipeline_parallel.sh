#!/usr/bin/env bash
# Paper 1 parallel pipeline. Turns the serial DAG into a parallel max.
#
# DAG:  B -> MB \
#       A -> M   >-- U  (control)
#       F -> MF2 /
#
# B, A, F are independent GPU jobs -> run concurrently, one per GPU.
# MB/M/MF2 are CPU post-processing -> fire the instant their parent ends.
# U runs once all three records JSONs exist.
#
# Usage:  bash scripts/smoke/pipeline_parallel.sh
# Env:    GPUS="0 1 2"  (default: all visible GPUs, else CPU/single)
set -uo pipefail
cd "$(dirname "$0")/../.."
mkdir -p runs logs

mapfile -t GPU_ARR < <(nvidia-smi -L 2>/dev/null | sed -n 's/^GPU \([0-9]\+\).*/\1/p')
[ ${#GPU_ARR[@]} -eq 0 ] && GPU_ARR=(0)
GPUS="${GPUS:-${GPU_ARR[*]}}"
read -r -a G <<< "$GPUS"
echo "# GPUs: ${G[*]}"

run_on() {  # run_on <gpu> <logname> <cmd...>
  local gpu="$1" name="$2"; shift 2
  ( CUDA_VISIBLE_DEVICES="$gpu" "$@" >"logs/$name.log" 2>&1
    echo "$? $name" >>logs/.done ) &
  echo "  launched $name on GPU$gpu (pid $!)"
}

: >logs/.done
T0=$(date +%s)

# --- Stage 1: three independent GPU passes, fanned across GPUs ---
echo "== Stage 1: B / A / F concurrently =="
run_on "${G[0]}"                 B python scripts/smoke/B_donut_cord_on_cord.py
run_on "${G[1%${#G[@]}]:-${G[0]}}" A python scripts/smoke/A_donut_cord_on_sroie.py
run_on "${G[2%${#G[@]}]:-${G[0]}}" F python scripts/smoke/F_layoutlmv3_on_wildreceipt.py

# --- Stage 2: each CPU post-process fires as soon as its parent JSON lands ---
wait_for() { while [ ! -s "runs/$1" ]; do sleep 3; done; }
( wait_for B_donut_cord_on_cord.json    ; python scripts/smoke/MB_cord_baseline.py        >logs/MB.log  2>&1; echo "$? MB"  >>logs/.done ) &
( wait_for A_donut_cord_on_sroie.json   ; python scripts/smoke/M_baseline_softmax.py      >logs/M.log   2>&1; echo "$? M"   >>logs/.done ) &
( wait_for F_layoutlmv3_on_wildreceipt.json; python scripts/smoke/MF2_wildreceipt_softmax.py >logs/MF2.log 2>&1; echo "$? MF2" >>logs/.done ) &

wait
echo "== Stage 3: U intersection-control =="
python scripts/smoke/U_intersection_control.py >logs/U.log 2>&1; echo "$? U" >>logs/.done

echo "# done in $(( $(date +%s) - T0 ))s"
echo "# exit codes:"; sort -u logs/.done
echo "# U verdict:"; grep -A2 '"verdict"' runs/U_intersection_control.json 2>/dev/null | head -3
