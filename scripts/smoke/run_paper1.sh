#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p runs

echo "=== Setup (pip install) ==="
pip install -q --upgrade pip
pip install -q transformers "datasets>=2.20.0,<3.0.0" pillow torch torchvision numpy scipy \
               sentencepiece protobuf accelerate certifi huggingface_hub pyarrow pytesseract

# Attempt tesseract-ocr install for I3 verification on SROIE.
# If apt isn't available or fails, A still runs (skips I3, reports F1 baseline only).
if command -v apt-get >/dev/null 2>&1; then
  apt-get install -y -q tesseract-ocr 2>/dev/null || echo "  (tesseract install skipped — I3 on SROIE will be skipped)"
fi

echo
echo "=== A: DONUT-CORD on canonical SROIE Task-3 (n=347, cross-corpus) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== B: DONUT-CORD on CORD-test (in-distribution) ==="
python scripts/smoke/B_donut_cord_on_cord.py

echo
echo "=== E: WildReceipt pre-flight ==="
python scripts/smoke/E_wildreceipt_preflight.py

echo
echo "=== Done. Results in runs/ ==="
ls -la runs/
