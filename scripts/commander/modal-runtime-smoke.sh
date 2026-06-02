#!/bin/bash
# Modal Runtime Smoke Test — Bayyinah + Mihwar
#
# Purpose
#   Prove that the Modal runtime is live by hitting /review and /generate
#   on the deployed Bayyinah and Mihwar endpoints. Designed to run in a CI
#   step with secrets bound, OR locally when the operator has bound the
#   required endpoint and token env vars. Fails closed on any missing
#   prerequisite.
#
# Required env (presence-only; values are NEVER echoed):
#   BAYYINAH_ENDPOINT   — Modal HTTPS URL ending in /bayyinah-review
#   MIHWAR_ENDPOINT     — Modal HTTPS URL ending in /mihwar-generate
#   BAYYINAH_API_TOKEN  — Bayyinah endpoint bearer token
#   MIHWAR_API_TOKEN    — Mihwar endpoint bearer token
#
# Output
#   On stdout: a status block in the format expected by
#   docs/launch-evidence/agent-launch.md §5. HTTP codes are reported.
#   Response bodies, prompts, and tokens are NEVER printed.
#
# Exit codes
#   0  READY   — both endpoints answered 2xx with non-empty JSON.
#   2  HOLD    — secrets unset; nothing was contacted.
#   3  BLOCK   — at least one endpoint failed (auth/timeout/non-2xx).
#   4  ERROR   — runtime prerequisite missing (curl, jq).
#
# Safety
#   - Bearer token is never written to logs, files, or argv.
#   - Endpoint URLs are reported only as host (no path or query).
#   - `set -e` + `set -u` guard against silent failures.
#   - The script does NOT call any model with user content; payload is a
#     fixed 1-line "ping" prompt that contains no secrets.

set -euo pipefail

# Never let xtrace leak secrets if the caller enabled it upstream.
set +x

# ── Prerequisite tools ─────────────────────────────────────────────────────
need() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "[ERROR] required tool not found: $1" >&2
        exit 4
    fi
}
need curl

# ── Presence-only secret check ─────────────────────────────────────────────
report_presence() {
    local name="$1"
    if [ -n "${!name:-}" ]; then
        echo "$name=SET"
    else
        echo "$name=UNSET"
    fi
}

echo "=== Modal Runtime Smoke — secrets ==="
report_presence BAYYINAH_ENDPOINT
report_presence MIHWAR_ENDPOINT
report_presence BAYYINAH_API_TOKEN
report_presence MIHWAR_API_TOKEN
echo

if [ -z "${BAYYINAH_ENDPOINT:-}" ] || \
   [ -z "${MIHWAR_ENDPOINT:-}" ] || \
   [ -z "${BAYYINAH_API_TOKEN:-}" ] || \
   [ -z "${MIHWAR_API_TOKEN:-}" ]; then
    echo "[HOLD] one or more secrets are UNSET; aborting before any network call."
    echo "[HOLD] bind BAYYINAH_ENDPOINT, MIHWAR_ENDPOINT, BAYYINAH_API_TOKEN, MIHWAR_API_TOKEN and re-run."
    # Canonical verdict label shared with .github/workflows/modal-runtime-activation.yml.
    # Missing secrets are a HOLD, never a FAIL.
    echo "STATUS=UNVERIFIED_SECRET_MISSING"
    exit 2
fi

# ── Helper: extract host from URL (no path, no query) ──────────────────────
host_of() {
    local url="$1"
    # strip protocol
    local rest="${url#*://}"
    # keep up to first '/'
    echo "${rest%%/*}"
}

# ── Helper: call endpoint and return only http_code ────────────────────────
# Body is captured to /tmp and immediately discarded after status extraction.
# We deliberately do NOT print or persist the response body to avoid
# accidentally surfacing prompt-completion content in CI logs.
hit_endpoint() {
    local label="$1"
    local url="$2"
    local token="$3"
    local payload="$4"
    local body_file
    body_file="$(mktemp)"
    local http_code
    # curl always emits %{http_code} (000 on transport failure), so do not
    # double-append a fallback. Fall back to "000" only if curl produced
    # no output at all.
    http_code="$(curl -sS -o "$body_file" -w '%{http_code}' \
        --max-time 60 \
        -X POST "$url" \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" \
        -H "X-Request-Id: smoke-$(date -u +%Y%m%dT%H%M%SZ)" \
        --data "$payload" 2>/dev/null)"
    http_code="${http_code:-000}"
    local body_size
    body_size="$(wc -c < "$body_file" | tr -d '[:space:]')"
    # Quick "is it JSON?" check without echoing content.
    local is_json="no"
    if head -c 1 "$body_file" 2>/dev/null | grep -qE '[{[]'; then
        is_json="yes"
    fi
    rm -f "$body_file"
    echo "$label host=$(host_of "$url") http_code=$http_code body_bytes=$body_size json=$is_json"
    case "$http_code" in
        2*) return 0 ;;
        *)  return 1 ;;
    esac
}

# ── Run smoke calls ────────────────────────────────────────────────────────
echo "=== Modal Runtime Smoke — endpoint probes ==="
status=0

bayyinah_payload='{"code":"def add(a, b):\n    return a + b","context":"smoke ping"}'
mihwar_payload='{"task":"smoke ping","constraints":"reply OK","max_tokens":16}'

if hit_endpoint "bayyinah" "$BAYYINAH_ENDPOINT" "$BAYYINAH_API_TOKEN" "$bayyinah_payload"; then
    bayyinah_verdict="PASS"
else
    bayyinah_verdict="FAIL"
    status=1
fi

if hit_endpoint "mihwar" "$MIHWAR_ENDPOINT" "$MIHWAR_API_TOKEN" "$mihwar_payload"; then
    mihwar_verdict="PASS"
else
    mihwar_verdict="FAIL"
    status=1
fi

echo
echo "=== Modal Runtime Smoke — verdict ==="
echo "bayyinah=$bayyinah_verdict mihwar=$mihwar_verdict"

if [ "$status" -ne 0 ]; then
    echo "[BLOCK] at least one endpoint failed; runtime is not READY."
    echo "STATUS=BLOCKED_MODAL_FAILURE"
    exit 3
fi

echo "[READY] both endpoints answered 2xx with JSON-shaped bodies."
echo "STATUS=VERIFIED_ENDPOINT_SMOKE"
echo "Now update docs/launch-evidence/agent-launch.md §5 with this run's"
echo "host + http_code values. Do NOT paste response bodies."
exit 0
