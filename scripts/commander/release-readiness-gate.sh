#!/usr/bin/env bash
set -u -o pipefail

# Release readiness gate — three-section verdict model:
#   1) REPOSITORY BASELINE      — static gates/tests (required, BLOCK on failure)
#   2) LOCAL OLLAMA RUNTIME     — official sovereign path (required for READY;
#                                 unexecuted smoke => HOLD, never READY)
#   3) PUBLIC RUNTIME           — Modal (legacy/optional) + public surface checks
#
# Modal is NOT a precondition for local sovereign readiness. Missing Modal
# secrets mark the Modal checks LEGACY-OPTIONAL/SKIPPED without holding the
# verdict. READY is impossible unless the Local Ollama smoke fully verifies:
#   - SELF_HOSTED_OLLAMA_SMOKE_NOT_EXECUTED
#   - LOCAL_GENERATION_NOT_VERIFIED
#   - OLLAMA_NO_CLOUD_NOT_VERIFIED

REPO_ROOT="${1:-.}"
cd "$REPO_ROOT" || exit 1

block_failures=0
hold_flags=0
local_ollama_smoke_verified=0

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

hold_with_reason() {
  local reason_code="$1"
  echo "[HOLD] $reason_code"
  hold_flags=$((hold_flags + 1))
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
echo "runtime-path policy: local_ollama=OFFICIAL_SOVEREIGN_PATH modal=LEGACY_OPTIONAL"
echo

echo "=== SECTION 1: REPOSITORY BASELINE ==="
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

echo "=== SECTION 2: LOCAL OLLAMA RUNTIME (OFFICIAL SOVEREIGN PATH) ==="
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_SMOKE_MODEL="${OLLAMA_SMOKE_MODEL:-qwen2.5:0.5b}"
OLLAMA_CURL_MAX_TIME="${OLLAMA_CURL_MAX_TIME:-15}"
echo "OLLAMA_BASE_URL=${OLLAMA_BASE_URL}"
echo

ollama_url_is_local() {
  python3 - "$OLLAMA_BASE_URL" <<'PY'
import sys
from urllib.parse import urlparse

parsed = urlparse(sys.argv[1])
allowed_hosts = {"localhost", "127.0.0.1", "::1", "ollama"}
if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed_hosts:
    raise SystemExit(1)
PY
}

manifest_declares_no_cloud_inference() {
  python3 - config/ollama.local.models.json <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
policy = data.get("policy", {})
if policy.get("egress") != "none_for_inference":
    raise SystemExit(1)
if policy.get("trustBoundary") != "LOCAL_CONTROL_PLANE":
    raise SystemExit(1)
PY
}

ollama_generation_smoke() {
  python3 - "$OLLAMA_BASE_URL" "$OLLAMA_SMOKE_MODEL" <<'PY'
import json
import sys
import urllib.request

base_url = sys.argv[1].rstrip("/")
model = sys.argv[2]
payload = json.dumps(
    {"model": model, "prompt": "Reply with the single word: VERIFIED", "stream": False}
).encode("utf-8")
request = urllib.request.Request(
    f"{base_url}/api/generate",
    data=payload,
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=120) as response:
    body = json.loads(response.read().decode("utf-8"))
if not str(body.get("response", "")).strip():
    raise SystemExit("local generation returned an empty response")
print(f"local generation ok: model={model} bytes={len(body.get('response', ''))}")
PY
}

if curl -fsS --max-time "$OLLAMA_CURL_MAX_TIME" "${OLLAMA_BASE_URL%/}/api/tags" >/dev/null 2>&1; then
  echo "[INFO] Self-hosted Ollama reachable at ${OLLAMA_BASE_URL}"
  echo
  section2_holds=0

  echo "[CHECK] Sovereign model-set presence (manifest)"
  if bash scripts/ollama/activate-local-models.sh; then
    echo "[PASS] Sovereign model-set presence (manifest)"
  else
    hold_with_reason "LOCAL_MODEL_SET_INCOMPLETE"
    section2_holds=$((section2_holds + 1))
  fi
  echo

  echo "[CHECK] Local generation smoke (${OLLAMA_SMOKE_MODEL})"
  if ollama_generation_smoke; then
    echo "[PASS] Local generation smoke"
  else
    hold_with_reason "LOCAL_GENERATION_NOT_VERIFIED"
    section2_holds=$((section2_holds + 1))
  fi
  echo

  echo "[CHECK] No-cloud posture (local-only base URL + manifest egress policy)"
  if ollama_url_is_local && manifest_declares_no_cloud_inference; then
    echo "[PASS] No-cloud posture"
  else
    hold_with_reason "OLLAMA_NO_CLOUD_NOT_VERIFIED"
    section2_holds=$((section2_holds + 1))
  fi
  echo

  if [ "$section2_holds" -eq 0 ]; then
    local_ollama_smoke_verified=1
    echo "LOCAL_OLLAMA_SMOKE=VERIFIED"
  else
    echo "LOCAL_OLLAMA_SMOKE=HOLD"
  fi
else
  echo "[INFO] Self-hosted Ollama is NOT reachable at ${OLLAMA_BASE_URL}"
  hold_with_reason "SELF_HOSTED_OLLAMA_SMOKE_NOT_EXECUTED"
  hold_with_reason "LOCAL_GENERATION_NOT_VERIFIED"
  hold_with_reason "OLLAMA_NO_CLOUD_NOT_VERIFIED"
  echo "LOCAL_OLLAMA_SMOKE=HOLD"
fi
echo

echo "=== SECTION 3: PUBLIC RUNTIME (MODAL = LEGACY/OPTIONAL) ==="
echo
echo "--- Secret state (presence only) ---"
missing_runtime_secret=0
for secret_name in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN MODAL_TOKEN_ID MODAL_TOKEN_SECRET; do
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
  echo "[LEGACY-OPTIONAL] Modal runtime checks skipped (missing Modal secrets)."
  echo "[LEGACY-OPTIONAL] Modal is not required for local sovereign readiness; this does not hold the verdict."
  echo
fi

echo "--- Public surface checks ---"
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
echo "sections: repository_baseline | local_ollama_runtime | public_runtime"
echo "block_failures=${block_failures} hold_flags=${hold_flags} local_ollama_smoke_verified=${local_ollama_smoke_verified}"

if [ "$block_failures" -gt 0 ]; then
  echo "BLOCK"
  exit 1
fi

if [ "$local_ollama_smoke_verified" -ne 1 ]; then
  echo "HOLD (READY forbidden until Local Ollama smoke is VERIFIED)"
  exit 2
fi

if [ "$hold_flags" -gt 0 ]; then
  echo "HOLD"
  exit 2
fi

echo "READY"
exit 0
