#!/usr/bin/env bash
# Paper 1 pipeline. Degrades correctly to 1 GPU (serialize, no fan-out)
# and FORCES fresh data (deletes committed runs/*.json so re-analysis
# never silently uses a stale cached pass).
#
# DAG:  B -> MB \
#       A -> M   >-- U
#       F -> MF2 /
#
# Usage:  bash scripts/smoke/pipeline_parallel.sh
# Env:    GPUS="0 1 2"  (default: auto-detect; "" or 1 entry => serial)
set -uo pipefail
cd "$(dirname "$0")/../.."
mkdir -p runs logs

mapfile -t GPU_ARR < <(nvidia-smi -L 2>/dev/null | sed -n 's/^GPU \([0-9]\+\).*/\1/p')
[ ${#GPU_ARR[@]} -eq 0 ] && GPU_ARR=(0)
read -r -a G <<< "${GPUS:-${GPU_ARR[*]}}"
# Clamp to the GPUs that actually exist on this box.
NREAL=${#GPU_ARR[@]}
if [ "${#G[@]}" -gt "$NREAL" ]; then G=("${GPU_ARR[@]}"); fi
NG=${#G[@]}
echo "# real GPUs=$NREAL ; using=${G[*]} ; mode=$([ $NG -le 1 ] && echo SERIAL || echo PARALLEL)"

# Force fresh: drop any committed/stale result JSONs for this pipeline.
rm -f runs/B_donut_cord_on_cord.json runs/MB_cord_baseline.json \
      runs/A_donut_cord_on_sroie.json runs/M_baseline_softmax.json \
      runs/F_layoutlmv3_on_wildreceipt.json runs/MF2_wildreceipt_softmax.json \
      runs/U_intersection_control.json
: >logs/.done
T0=$(date +%s)

runlog() { local name="$1"; shift; echo "  >> $name"; "$@" >"logs/$name.log" 2>&1; echo "$? $name" >>logs/.done; }

if [ "$NG" -le 1 ]; then
  GP="${G[0]}"
  export CUDA_VISIBLE_DEVICES="$GP"
  echo "== SERIAL on GPU$GP (1-GPU box): dependency order =="
  runlog B   python scripts/smoke/B_donut_cord_on_cord.py
  runlog MB  python scripts/smoke/MB_cord_baseline.py
  runlog A   python scripts/smoke/A_donut_cord_on_sroie.py
  runlog M   python scripts/smoke/M_baseline_softmax.py
  runlog F   python scripts/smoke/F_layoutlmv3_on_wildreceipt.py
  runlog MF2 python scripts/smoke/MF2_wildreceipt_softmax.py
  runlog U   python scripts/smoke/U_intersection_control.py
  runlog U2  python scripts/smoke/U2_orthogonality.py
  runlog U3  python scripts/smoke/U3_risk_coverage.py
else
  echo "== PARALLEL: B/A/F across GPUs =="
  ( CUDA_VISIBLE_DEVICES="${G[0]}" python scripts/smoke/B_donut_cord_on_cord.py >logs/B.log 2>&1
    python scripts/smoke/MB_cord_baseline.py >logs/MB.log 2>&1; echo "$? B+MB" >>logs/.done ) &
  ( CUDA_VISIBLE_DEVICES="${G[1]}" python scripts/smoke/A_donut_cord_on_sroie.py >logs/A.log 2>&1
    python scripts/smoke/M_baseline_softmax.py >logs/M.log 2>&1; echo "$? A+M" >>logs/.done ) &
  ( CUDA_VISIBLE_DEVICES="${G[2%$NG]}" python scripts/smoke/F_layoutlmv3_on_wildreceipt.py >logs/F.log 2>&1
    python scripts/smoke/MF2_wildreceipt_softmax.py >logs/MF2.log 2>&1; echo "$? F+MF2" >>logs/.done ) &
  wait
  CUDA_VISIBLE_DEVICES="${G[0]}" python scripts/smoke/U_intersection_control.py >logs/U.log 2>&1
  echo "$? U" >>logs/.done
  python scripts/smoke/U2_orthogonality.py >logs/U2.log 2>&1; echo "$? U2" >>logs/.done
  python scripts/smoke/U3_risk_coverage.py >logs/U3.log 2>&1; echo "$? U3" >>logs/.done
fi

echo "# done in $(( $(date +%s) - T0 ))s"
echo "# exit codes:"; sort -u logs/.done
echo "# U verdict:"; grep -A2 '"verdict"' runs/U_intersection_control.json 2>/dev/null | head -3
