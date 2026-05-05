#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

echo "[P0] Running Bayyinah + Router Policy test gate"
python -m unittest \
  tests.test_bayyinah_validation_gate \
  tests.test_router_policy
