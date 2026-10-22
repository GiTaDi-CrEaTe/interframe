#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/2] Running Interframe Scientific Benchmark (B1, B2, B3)..."
python3 evaluation/evaluate_baselines.py

echo "[2/2] Running Unit and Integration Test Suite..."
python3 -m unittest discover -s tests -t . -p "test_*.py" -v
echo "All Interframe verification gates passed."
