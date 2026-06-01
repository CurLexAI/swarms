#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Licensed under MIT
#
# Fail-closed preflight that MUST pass before any Modal agent activation.
# Verifies repo state, Python version, required-secret PRESENCE (never values),
# static security audits, agent validation, tests, and policy gates.
#
# Secrets are checked for presence only. This script never prints secret values.
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

require_env_present() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    fail "missing env: $name"
  fi
  echo "env_present: $name"
}

echo "[repo]"
git remote get-url origin >/dev/null 2>&1 || fail "origin missing"
git rev-parse --is-inside-work-tree >/dev/null
git status --short

echo "[python]"
python3 - <<'PY'
import sys
allowed = {(3, 11), (3, 12)}
version = sys.version_info[:2]
if version not in allowed:
    raise SystemExit(
        f"FAIL: Python {version[0]}.{version[1]} not allowed for Modal "
        "activation; use 3.11 or 3.12"
    )
print(f"python_ok: {version[0]}.{version[1]}")
PY

echo "[secrets presence only]"
require_env_present MODAL_TOKEN_ID
require_env_present MODAL_TOKEN_SECRET
require_env_present HF_TOKEN
require_env_present BAYYINAH_API_TOKEN
require_env_present MIHWAR_API_TOKEN
require_env_present BAYYINAH_MODEL_REVISION
require_env_present MIHWAR_MODEL_REVISION
require_env_present QDRANT_INTERNAL_URL
require_env_present QDRANT_API_KEY

echo "[secret static audit]"
python3 scripts/security/static_audit.py .

echo "[runtime policy audit]"
python3 scripts/security/runtime_policy_audit.py .

echo "[python compile]"
python3 -m py_compile .agents/*.py

echo "[agent validation]"
python3 .agents/validate.py
python3 .agents/invoke.py info

echo "[tests]"
python3 -m pytest -q tests/

echo "[gates]"
bash scripts/commander/agent-presence-gate.sh .
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .

echo "AGENT_ACTIVATION_PREFLIGHT=PASS"
