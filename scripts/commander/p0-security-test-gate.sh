#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

echo "[P0] Running Bayyinah + Router Policy test gate"
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[FAIL] python3/python not found"
  exit 1
fi
"$PY" -m unittest \
  tests.test_bayyinah_validation_gate \
  tests.test_router_policy
