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

# Shelved (stable; not in base run): B_donut_cord_on_cord, E_wildreceipt_preflight,
# F_layoutlmv3_on_wildreceipt. Result JSONs from prior runs are the headline numbers
# for the 3-corpus story. Re-run manually if needed.

echo
echo "=== A v11: DONUT-SROIE on canonical SROIE Task-3 (in-dist, n=347, bare-int filtered tau) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== G v10/v11: cardinality-guard ablation + DP latency + money-count buckets (CPU) ==="
python scripts/smoke/G_robustness.py

echo
echo "=== L: SROIE failure-mode diagnostic (CPU, reads A's output) ==="
python scripts/smoke/L_sroie_failure_modes.py

echo
echo "=== K v2: DocILE-like 4th corpus (bonus, in-dist labeled-amounts regime) ==="
python scripts/smoke/K_docile.py || echo "  K returned non-zero; continuing (bonus only)"

echo
echo "=== Done. Active results in runs/ ==="
ls -la runs/
