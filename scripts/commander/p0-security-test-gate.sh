#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

echo "[P0] Running Bayyinah + Router + Aegis MCP security test gate"
if [[ -n "${PYTHON_BIN:-}" ]]; then
  :
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "[FAIL] PYTHON_NOT_FOUND: python3 or python is required"
  exit 1
fi

"$PYTHON_BIN" -m unittest \
  tests.test_bayyinah_validation_gate \
  tests.test_router_policy \
  tests.test_aegis_mcp_gateway
