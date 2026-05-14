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

# Shelved (stable; not in base run): B/E/F.

echo
echo "=== A v13: DONUT-SROIE + I3 multi-candidate tau (in-dist, n=347) ==="
python scripts/smoke/A_donut_cord_on_sroie.py

echo
echo "=== G: cardinality-guard ablation + DP latency + money-count buckets (CPU) ==="
python scripts/smoke/G_robustness.py

echo
echo "=== L: SROIE failure-mode diagnostic (CPU) ==="
python scripts/smoke/L_sroie_failure_modes.py

echo
echo "=== M: softmax-threshold baseline comparison vs sigma (GPU, ~2 min) ==="
python scripts/smoke/M_baseline_softmax.py

echo
echo "=== K v4: DocILE n=501 pooled (bonus, clean-regime validation) ==="
python scripts/smoke/K_docile.py || echo "  K returned non-zero; continuing (bonus only)"

echo
echo "=== Done. Active results in runs/ ==="
ls -la runs/
