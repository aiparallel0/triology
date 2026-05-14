#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p runs

echo "=== Setup (pip install) ==="
pip install -q --upgrade pip
pip install -q transformers "datasets>=2.20.0,<3.0.0" pillow torch torchvision numpy scipy sentencepiece protobuf accelerate

echo
echo "=== A: DONUT-CORD on SROIE-347 (cross-corpus) ==="
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
