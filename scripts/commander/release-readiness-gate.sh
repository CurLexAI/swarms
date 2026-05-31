#!/usr/bin/env bash
set -u -o pipefail

REPO_ROOT="${1:-.}"
cd "$REPO_ROOT" || exit 1

block_failures=0
hold_flags=0

run_required_check() {
  local label="$1"
  local cmd="$2"
  echo "[CHECK] $label"
  if eval "$cmd"; then
    echo "[PASS] $label"
  else
    echo "[FAIL] $label"
    block_failures=$((block_failures + 1))
  fi
  echo
}

run_optional_runtime_check() {
  local label="$1"
  local cmd="$2"
  echo "[RUNTIME] $label"
  if eval "$cmd"; then
    echo "[PASS] $label"
  else
    echo "[FAIL] $label"
    block_failures=$((block_failures + 1))
  fi
  echo
}

require_env() {
  local name="$1"
  if [ -n "${!name:-}" ]; then
    echo "$name=SET"
    return 0
  fi
  echo "$name=UNSET"
  return 1
}

echo "=== RELEASE READINESS GATE ==="
echo "repo=$(pwd)"
echo

run_required_check "Python syntax compile" "python3 -m py_compile .agents/*.py"
run_required_check "Agent config validation" "python3 .agents/validate.py"
run_required_check "Agent inventory command" "python3 .agents/invoke.py info"

run_required_check "P0 security test gate" "bash scripts/commander/p0-security-test-gate.sh ."
run_required_check "Modal boundary gate" "bash scripts/commander/modal-boundary-gate.sh ."
run_required_check "ADR-0001 boundary gate" "bash scripts/commander/adr-0001-boundary-gate.sh ."
run_required_check "Agent presence gate" "bash scripts/commander/agent-presence-gate.sh ."
run_required_check "Strict swarm presence monitor" "npm run check:swarms-presence:strict"
run_required_check "Codex commander gate" "bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh ."
run_required_check "Qal'a audit integrity gate" "bash scripts/commander/qala-audit-integrity-gate.sh ."

run_required_check "Python tests" "python3 -m pytest -q tests/"
run_required_check "Node unit tests" "npm run test:unit"
run_required_check "Node security tests" "npm run test:security"
run_required_check "TypeScript check" "npx tsc --noEmit"
run_required_check "Aggregate repo check" "npm run check"
run_required_check "Node full tests" "npm test"

echo "=== SECRET STATE (presence only) ==="
missing_runtime_secret=0
for secret_name in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT AGENT_API_TOKEN MODAL_TOKEN_ID MODAL_TOKEN_SECRET; do
  if ! require_env "$secret_name"; then
    missing_runtime_secret=1
  fi
done
echo

if [ "$missing_runtime_secret" -eq 0 ]; then
  run_optional_runtime_check "Modal deploy" "modal deploy .agents/modal_app.py"
  run_optional_runtime_check "Mihwar smoke test" "modal run .agents/modal_app.py::test_mihwar"
  run_optional_runtime_check "Bayyinah smoke test" "modal run .agents/modal_app.py::test_bayyinah"
else
  echo "[HOLD] Runtime smoke checks skipped (missing runtime secrets)"
  hold_flags=$((hold_flags + 1))
  echo
fi

echo "=== PUBLIC SURFACE CHECKS ==="
PUBLIC_SURFACE_ORIGIN="${PUBLIC_SURFACE_ORIGIN:-}"
PUBLIC_SURFACE_APEX="${PUBLIC_SURFACE_APEX:-}"

if [ -n "$PUBLIC_SURFACE_ORIGIN" ] && [ -n "$PUBLIC_SURFACE_APEX" ]; then
  run_required_check "Public root headers" "curl -fsSI \"$PUBLIC_SURFACE_ORIGIN\" >/tmp/release_root_headers.txt"
  run_required_check "Public apex redirect" "curl -fsSI \"$PUBLIC_SURFACE_APEX\" >/tmp/release_apex_headers.txt"
  run_required_check "Admin route protected" "curl -fsSI \"$PUBLIC_SURFACE_ORIGIN/admin\" >/tmp/release_admin_headers.txt"
  run_required_check "API route protected" "curl -fsSI \"$PUBLIC_SURFACE_ORIGIN/api\" >/tmp/release_api_headers.txt"

  if ! rg -q "strict-transport-security" /tmp/release_root_headers.txt; then
    echo "[FAIL] Missing strict-transport-security on public root"
    block_failures=$((block_failures + 1))
  fi
  if ! rg -q "content-security-policy" /tmp/release_root_headers.txt; then
    echo "[FAIL] Missing content-security-policy on public root"
    block_failures=$((block_failures + 1))
  fi
  if ! rg -q "x-content-type-options" /tmp/release_root_headers.txt; then
    echo "[FAIL] Missing x-content-type-options on public root"
    block_failures=$((block_failures + 1))
  fi
  if ! rg -q "referrer-policy" /tmp/release_root_headers.txt; then
    echo "[FAIL] Missing referrer-policy on public root"
    block_failures=$((block_failures + 1))
  fi
  if ! rg -q "x-frame-options|frame-ancestors" /tmp/release_root_headers.txt; then
    echo "[FAIL] Missing clickjacking protection on public root"
    block_failures=$((block_failures + 1))
  fi
  if ! rg -q "permissions-policy" /tmp/release_root_headers.txt; then
    echo "[HOLD] permissions-policy header not found on public root"
    hold_flags=$((hold_flags + 1))
  fi
  if ! rg -q "HTTP/2 401|HTTP/1.1 401|HTTP/2 403|HTTP/1.1 403" /tmp/release_admin_headers.txt; then
    echo "[FAIL] /admin is not protected by 401/403"
    block_failures=$((block_failures + 1))
  fi
  if ! rg -q "HTTP/2 401|HTTP/1.1 401|HTTP/2 403|HTTP/1.1 403" /tmp/release_api_headers.txt; then
    echo "[FAIL] /api is not protected by 401/403"
    block_failures=$((block_failures + 1))
  fi
else
  echo "[HOLD] Public surface checks skipped (set PUBLIC_SURFACE_ORIGIN and PUBLIC_SURFACE_APEX)"
  hold_flags=$((hold_flags + 1))
fi
echo

echo "=== VERDICT ==="
if [ "$block_failures" -gt 0 ]; then
  echo "BLOCK"
  exit 1
fi

if [ "$hold_flags" -gt 0 ]; then
  echo "HOLD"
  exit 2
fi

echo "READY"
exit 0
