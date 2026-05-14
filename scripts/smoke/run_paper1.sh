#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p runs

echo "=== Setup (pip install) ==="
pip install -q --upgrade pip
pip install -q transformers "datasets>=2.20.0,<3.0.0" pillow torch torchvision numpy scipy \
               sentencepiece protobuf accelerate certifi huggingface_hub pyarrow pytesseract

if command -v apt-get >/dev/null 2>&1; then
  apt-get install -y -q tesseract-ocr 2>/dev/null || true
fi

# Shelved (stable; not in base run):
#   B, E, F  — headline 3-corpus numbers locked
#   L        — SROIE failure-mode taxonomy; stable
#   K v4     — DocILE identity rate; stable
#   N        — net-F1 / cost analysis; stable
#   P        — error-type taxonomy; stable
#   S        — Pareto frontier; stable
# Re-run any of these manually if needed.

echo
echo "=== A v13: DONUT-SROIE + I3 multi-candidate tau (headline) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== G: cardinality-guard ablation + DP latency + SROIE money-count buckets ==="
python scripts/smoke/G_robustness.py

echo
echo "=== GB: sigma money-count bucket analysis on CORD ==="
python scripts/smoke/GB_cord_buckets.py

echo
echo "=== L_cord: sigma failure-mode taxonomy on CORD ==="
python scripts/smoke/L_cord.py

echo
echo "=== M: softmax baseline on SROIE ==="
python scripts/smoke/M_baseline_softmax.py

echo
echo "=== MB: softmax baseline on CORD ==="
python scripts/smoke/MB_cord_baseline.py

echo
echo "=== MF: WildReceipt (deferred; reports sigma-from-F) ==="
python scripts/smoke/MF_wildreceipt_baseline.py

echo
echo "=== Q v2: synthetic money-line noise sensitivity on CORD (10 seeds) ==="
python scripts/smoke/Q_money_noise_cord.py

echo
echo "=== V: sigma epsilon-tolerance sweep on CORD ==="
python scripts/smoke/V_tolerance_sweep_cord.py

echo
echo "=== sigma_reliability_cord: precision binned by T_size on CORD ==="
python scripts/smoke/sigma_reliability_cord.py

echo
echo "=== time_budget: DONUT vs sigma DP per-receipt timing ==="
python scripts/smoke/time_budget.py

echo
echo "=== T: statistical significance tests (McNemar + Wilson CIs + bootstrap) ==="
python scripts/smoke/T_significance.py

echo
echo "=== paper_table: aggregate all locked numbers into PAPER_TABLE.{json,md,tex} ==="
python scripts/smoke/paper_table.py

echo
echo "=== Done. Active results in runs/ ==="
ls -la runs/
