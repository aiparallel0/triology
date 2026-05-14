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
#   B, E, F  — headline 3-corpus numbers locked in their JSONs
#   L        — failure-mode counts shift across extractor versions but the
#              dominant categories are now stable; rerun only when changing A
#   K v4     — DocILE identity rate (~60% sum=total) is stable across extractor versions
# Re-run any of these manually if needed.

echo
echo "=== A v13: DONUT-SROIE + I3 multi-candidate tau (headline) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== G: cardinality-guard ablation + DP latency + money-count buckets ==="
python scripts/smoke/G_robustness.py

echo
echo "=== M: softmax baseline on SROIE ==="
python scripts/smoke/M_baseline_softmax.py

echo
echo "=== MB: softmax baseline on CORD ==="
python scripts/smoke/MB_cord_baseline.py

echo
echo "=== MF: softmax baseline on WildReceipt ==="
python scripts/smoke/MF_wildreceipt_baseline.py

echo
echo "=== N: net-F1 / cost-sensitive deployment analysis (defends: 'what's deployment value?') ==="
python scripts/smoke/N_net_F1.py

echo
echo "=== P: error-type taxonomy for sigma vs softmax orthogonality (defends: 'is orthogonality principled?') ==="
python scripts/smoke/P_error_taxonomy.py

echo
echo "=== Q: synthetic money-line noise sensitivity on CORD (defends: 'does sigma need clean labels?') ==="
python scripts/smoke/Q_money_noise_cord.py

echo
echo "=== S: Pareto frontier of (precision, coverage) (defends: 'is sigma's operating point principled?') ==="
python scripts/smoke/S_pareto.py

echo
echo "=== Done. Active results in runs/ ==="
ls -la runs/
