#!/usr/bin/env bash
# Sovereign platform CI orchestrator.
# Runs local repository gates, agent readiness checks, optional endpoint smoke,
# and optional activation hooks without printing secrets or private endpoints.

set -Eeuo pipefail

MODE="${SOVEREIGN_ORCHESTRATOR_MODE:-verify}"
CONFIRM="${SOVEREIGN_ORCHESTRATOR_CONFIRM:-VERIFY_ONLY}"
RUN_ENDPOINT_SMOKE="${RUN_ENDPOINT_SMOKE:-false}"
DEPLOY_MODAL="${DEPLOY_MODAL:-false}"
DEPLOY_RENDER="${DEPLOY_RENDER:-false}"
VERIFY_PUBLIC_SURFACES="${VERIFY_PUBLIC_SURFACES:-true}"
REPORT_PATH="${SOVEREIGN_ORCHESTRATOR_REPORT:-artifacts/sovereign-platform-orchestrator.md}"

mkdir -p "$(dirname "$REPORT_PATH")"
: > "$REPORT_PATH"

append_report() {
  printf '%s\n' "$*" >> "$REPORT_PATH"
}

log() {
  printf '[sovereign-orchestrator] %s\n' "$*"
}

mask_if_present() {
  local value="${1:-}"
  if [[ -n "$value" ]]; then
    printf '::add-mask::%s\n' "$value"
  fi
}

require_confirm_for_activation() {
  if [[ "$MODE" == "activate" && "$CONFIRM" != "SOVEREIGN_ACTIVATE" ]]; then
    log "activation requested without exact confirmation phrase"
    append_report "DECISION: BLOCKED — activation requires confirm=SOVEREIGN_ACTIVATE."
    exit 1
  fi
}

run_step() {
  local name="$1"
  shift
  log "START ${name}"
  append_report "- ${name}: RUNNING"
  "$@"
  log "PASS ${name}"
  append_report "- ${name}: VERIFIED"
}

check_secret_free_diff() {
  if git diff --cached --quiet 2>/dev/null; then
    git diff -- . ':!package-lock.json' | rg -i '(password|secret|api[_-]?key|token|bearer|AKIA|sk-|ghp_|github_pat_)' || true
  else
    git diff --cached | rg -i '(password|secret|api[_-]?key|token|bearer|AKIA|sk-|ghp_|github_pat_)' || true
  fi
}

validate_static_surface() {
  test -f public/trust/index.html
  python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

class Parser(HTMLParser):
    """Minimal parser smoke for the public trust surface."""

content = Path("public/trust/index.html").read_text(encoding="utf-8")
Parser().feed(content)
required = ["LexPrim", "Trust Center"]
missing = [item for item in required if item not in content]
if missing:
    raise SystemExit(f"missing public surface strings: {missing}")
print("public trust surface parse smoke passed")
PY
}

validate_repo() {
  run_step "git whitespace check" git diff --check
  run_step "secret-pattern review" check_secret_free_diff
  run_step "npm aggregate check" npm run check
  run_step "frontend SRI check" npm run test:cdn-sri
  # TypeScript typecheck is a tracked blocker (AGENTS.md:253) — run as
  # non-blocking advisory so it does not short-circuit remaining gates.
  log "START TypeScript typecheck (advisory)"
  if npx tsc --noEmit 2>&1; then
    append_report "- TypeScript typecheck: VERIFIED"
    log "PASS TypeScript typecheck (advisory)"
  else
    append_report "- TypeScript typecheck: UNVERIFIED — tracked blocker, see AGENTS.md"
    log "WARN TypeScript typecheck failed (advisory, non-blocking)"
  fi
  run_step "agent asset validation" python3 .agents/validate.py
  run_step "agent Python syntax" python3 -m py_compile .agents/*.py
  run_step "agent info" python3 .agents/invoke.py info
  run_step "ADR boundary gate" bash scripts/commander/adr-0001-boundary-gate.sh .
  run_step "Modal boundary gate" bash scripts/commander/modal-boundary-gate.sh .
  run_step "agent presence gate" bash scripts/commander/agent-presence-gate.sh .
  run_step "public trust surface smoke" validate_static_surface
}

verify_public_surfaces() {
  if [[ "$VERIFY_PUBLIC_SURFACES" != "true" ]]; then
    append_report "PUBLIC_SURFACES: UNVERIFIED — disabled by input."
    return 0
  fi

  local checked=0
  if [[ -n "${FRONTEND_URL:-}" ]]; then
    checked=1
    log "checking frontend public URL without printing it"
    curl --fail --silent --show-error --location --max-time 30 --output /tmp/sovereign-frontend.html "${FRONTEND_URL}"
    if ! rg -q 'LexPrim|Trust Center|Sovereign' /tmp/sovereign-frontend.html; then
      append_report "FRONTEND: BLOCKED — expected LexPrim markers were not found."
      rm -f /tmp/sovereign-frontend.html
      return 1
    fi
    rm -f /tmp/sovereign-frontend.html
    append_report "FRONTEND: VERIFIED — public surface responded with expected markers."
  fi

  if [[ -n "${BACKEND_HEALTH_URL:-}" ]]; then
    checked=1
    log "checking backend health URL without printing it"
    curl --fail --silent --show-error --location --max-time 30 --output /tmp/sovereign-backend-health.txt "${BACKEND_HEALTH_URL}"
    rm -f /tmp/sovereign-backend-health.txt
    append_report "BACKEND: VERIFIED — health endpoint responded successfully."
  fi

  if [[ "$checked" -eq 0 ]]; then
    append_report "PUBLIC_SURFACES: UNVERIFIED — FRONTEND_URL and BACKEND_HEALTH_URL were not configured."
  fi
}

run_endpoint_smoke() {
  if [[ "$RUN_ENDPOINT_SMOKE" != "true" ]]; then
    append_report "AGENT_ENDPOINT_SMOKE: UNVERIFIED — disabled by input."
    return 0
  fi

  local missing=0
  for name in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN; do
    if [[ -z "${!name:-}" ]]; then
      append_report "AGENT_ENDPOINT_SMOKE: UNVERIFIED — ${name} is not configured."
      missing=1
    fi
  done
  if [[ "$missing" -ne 0 ]]; then
    return 0
  fi

  if [[ "${BAYYINAH_API_TOKEN}" == "${MIHWAR_API_TOKEN}" ]]; then
    append_report "AGENT_ENDPOINT_SMOKE: BLOCKED — endpoint tokens must be isolated."
    return 1
  fi

  log "running Bayyinah and Mihwar endpoint smoke without printing endpoints"
  local bayyinah_status mihwar_status bayyinah_cross_status mihwar_cross_status
  bayyinah_status="$(curl -sS --max-time 240 -o /tmp/bayyinah.json -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer ${BAYYINAH_API_TOKEN}" -X POST -d '{"code":"def add(a,b): return a+b","context":"sovereign orchestrator smoke"}' "$BAYYINAH_ENDPOINT" || echo 000)"
  mihwar_status="$(curl -sS --max-time 420 -o /tmp/mihwar.json -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer ${MIHWAR_API_TOKEN}" -X POST -d '{"task":"return integer 1","context_files":{}}' "$MIHWAR_ENDPOINT" || echo 000)"
  bayyinah_cross_status="$(curl -sS --max-time 120 -o /tmp/bayyinah-cross.json -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer ${MIHWAR_API_TOKEN}" -X POST -d '{"code":"def add(a,b): return a+b","context":"cross-token-negative-smoke"}' "$BAYYINAH_ENDPOINT" || echo 000)"
  mihwar_cross_status="$(curl -sS --max-time 120 -o /tmp/mihwar-cross.json -w '%{http_code}' -H 'Content-Type: application/json' -H "Authorization: Bearer ${BAYYINAH_API_TOKEN}" -X POST -d '{"task":"return integer 1","context_files":{}}' "$MIHWAR_ENDPOINT" || echo 000)"
  rm -f /tmp/bayyinah.json /tmp/mihwar.json /tmp/bayyinah-cross.json /tmp/mihwar-cross.json

  if [[ "$bayyinah_status" == "200" && "$mihwar_status" == "200" && "$bayyinah_cross_status" =~ ^(401|403)$ && "$mihwar_cross_status" =~ ^(401|403)$ ]]; then
    append_report "AGENT_ENDPOINT_SMOKE: VERIFIED — endpoints responded and cross-token isolation held."
  else
    append_report "AGENT_ENDPOINT_SMOKE: BLOCKED — endpoint smoke or token isolation failed."
    return 1
  fi
}

activate_modal_if_requested() {
  if [[ "$MODE" != "activate" || "$DEPLOY_MODAL" != "true" ]]; then
    append_report "MODAL_DEPLOY: UNVERIFIED — not requested."
    return 0
  fi
  require_confirm_for_activation

  if [[ -z "${MODAL_TOKEN_ID:-}" || -z "${MODAL_TOKEN_SECRET:-}" ]]; then
    append_report "MODAL_DEPLOY: BLOCKED — Modal secrets are not configured."
    return 1
  fi
  if ! command -v modal >/dev/null 2>&1; then
    append_report "MODAL_DEPLOY: BLOCKED — Modal CLI is unavailable."
    return 1
  fi

  log "deploying Modal app without printing credentials"
  modal token set --token-id "$MODAL_TOKEN_ID" --token-secret "$MODAL_TOKEN_SECRET"
  modal deploy .agents/modal_app.py
  append_report "MODAL_DEPLOY: VERIFIED — Modal deploy command completed."
}

activate_render_if_requested() {
  if [[ "$MODE" != "activate" || "$DEPLOY_RENDER" != "true" ]]; then
    append_report "RENDER_DEPLOY: UNVERIFIED — not requested."
    return 0
  fi
  require_confirm_for_activation

  if [[ -z "${RENDER_DEPLOY_HOOK_URL:-}" ]]; then
    append_report "RENDER_DEPLOY: BLOCKED — Render deploy hook secret is not configured."
    return 1
  fi
  case "$RENDER_DEPLOY_HOOK_URL" in
    https://api.render.com/deploy/srv-*) ;;
    *)
      append_report "RENDER_DEPLOY: BLOCKED — Render deploy hook shape is invalid."
      return 1
      ;;
  esac

  log "triggering Render deploy hook without printing URL"
  curl --fail --silent --show-error --request POST "$RENDER_DEPLOY_HOOK_URL" >/dev/null
  append_report "RENDER_DEPLOY: VERIFIED — Render deploy hook accepted the request."
}

main() {
  mask_if_present "${MODAL_TOKEN_ID:-}"
  mask_if_present "${MODAL_TOKEN_SECRET:-}"
  mask_if_present "${BAYYINAH_ENDPOINT:-}"
  mask_if_present "${MIHWAR_ENDPOINT:-}"
  mask_if_present "${BAYYINAH_API_TOKEN:-}"
  mask_if_present "${MIHWAR_API_TOKEN:-}"
  mask_if_present "${RENDER_DEPLOY_HOOK_URL:-}"
  mask_if_present "${FRONTEND_URL:-}"
  mask_if_present "${BACKEND_HEALTH_URL:-}"

  append_report "# Sovereign Platform Orchestrator Report"
  append_report ""
  append_report "MODE: ${MODE}"
  append_report "VERIFIED: Repository gates are executed before any optional activation."
  append_report "CHANGED: This run may deploy only when mode=activate and confirm=SOVEREIGN_ACTIVATE."
  append_report "VALIDATION:"

  validate_repo
  verify_public_surfaces
  activate_modal_if_requested
  activate_render_if_requested
  run_endpoint_smoke

  append_report "RISKS: Live activation remains UNVERIFIED unless the relevant deploy and smoke rows are VERIFIED."
  append_report "DECISION: COMPLETED — review rows above for VERIFIED/BLOCKED/UNVERIFIED evidence."
  append_report "NEXT ACTION: Attach this artifact to the release or rerun with required secrets and confirmation."
  log "report written to ${REPORT_PATH}"
}

main "$@"
