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

echo
echo "=== A: DONUT-SROIE on canonical SROIE Task-3 (in-dist, n=347, labeled OCR) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== B: DONUT-CORD on CORD-test (in-dist, n=100) ==="
python scripts/smoke/B_donut_cord_on_cord.py

echo
echo "=== E: WildReceipt pre-flight (availability-only, CPU) ==="
python scripts/smoke/E_wildreceipt_preflight.py

echo
echo "=== F: LayoutLMv3-WildReceipt on WildReceipt-test (in-dist, n=472) ==="
python scripts/smoke/F_layoutlmv3_on_wildreceipt.py

echo
echo "=== G: cardinality-guard ablation + real-data DP latency (CPU) ==="
python scripts/smoke/G_robustness.py

echo
echo "=== Done. Results in runs/ ==="
ls -la runs/
