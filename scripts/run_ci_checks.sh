#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="python3"
if [ -x ".venv/bin/python3" ]; then
    PYTHON_BIN=".venv/bin/python3"
fi

echo "[1/2] Running Interframe Benchmark Evaluation (B1, B2, B3)..."
"$PYTHON_BIN" evaluation/evaluate_baselines.py

echo "[2/2] Running Unit and Integration Test Suite..."
"$PYTHON_BIN" -m unittest discover -s tests -t . -p "test_*.py" -v
echo "All Interframe verification gates passed."
