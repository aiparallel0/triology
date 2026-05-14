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

# Shelved (stable; not in base run): B/E/F have locked headline numbers in their
# JSONs. MB/MF re-run inference to get softmax scores and compare to sigma.

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
echo "=== M: softmax-threshold baseline vs sigma on SROIE (GPU, ~1 min) ==="
python scripts/smoke/M_baseline_softmax.py

echo
echo "=== MB: softmax-threshold baseline vs sigma on CORD (GPU, ~1 min) ==="
python scripts/smoke/MB_cord_baseline.py

echo
echo "=== MF: softmax-threshold baseline vs sigma on WildReceipt (GPU, ~30s) ==="
python scripts/smoke/MF_wildreceipt_baseline.py

echo
echo "=== K v4: DocILE n=501 (bonus, in-dist labeled-amounts regime) ==="
python scripts/smoke/K_docile.py || echo "  K returned non-zero; continuing (bonus only)"

echo
echo "=== Done. Active results in runs/ ==="
ls -la runs/
