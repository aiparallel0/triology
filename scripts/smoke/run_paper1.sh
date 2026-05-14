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
# F_layoutlmv3_on_wildreceipt. Their result JSONs are locked from prior runs and are
# the headline numbers in the 3-corpus story. Re-run manually if needed.

echo
echo "=== A v10: DONUT-SROIE on canonical SROIE Task-3 (in-dist, n=347, precise tau) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== G v10: cardinality-guard ablation + DP latency + money-count buckets (CPU) ==="
python scripts/smoke/G_robustness.py

echo
echo "=== K: DocILE 4th corpus (bonus, in-dist labeled-amounts regime) ==="
python scripts/smoke/K_docile.py || echo "  K returned non-zero; continuing (bonus only)"

echo
echo "=== Done. Active results in runs/ ==="
ls -la runs/
