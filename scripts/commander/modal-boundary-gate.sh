#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

status="PASS"
ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
info() { echo "[INFO] $*"; }

info "Modal boundary gate"
info "repo=$(pwd)"

# ── 1. No direct Modal endpoint URLs in client/public/server-rendered paths ──
PUBLIC_DIRS=(src public app pages components)
EXISTING_DIRS=()
for d in "${PUBLIC_DIRS[@]}"; do
  [[ -d "$d" ]] && EXISTING_DIRS+=("$d")
done

if (( ${#EXISTING_DIRS[@]} > 0 )); then
  if grep -RIn \
       --exclude-dir=.git --exclude-dir=node_modules \
       --exclude-dir=.next --exclude-dir=dist --exclude-dir=build \
       '\.modal\.run' "${EXISTING_DIRS[@]}" 2>/dev/null; then
    fail "MODAL_URL_LEAK: direct *.modal.run reference in public/client paths"
  else
    ok "no *.modal.run reference in $(IFS=, ; echo "${EXISTING_DIRS[*]}")"
  fi
else
  warn "no public/client directories to scan (skipped)"
fi

# ── 2. Modal SDK must not be imported from client/public surfaces ────────────
# Covers four shapes that all pull in the Modal SDK:
#   from "modal" / from 'modal'                  — bindings import
#   require("modal") / require('modal')          — CommonJS
#   import "modal" / import 'modal'              — side-effect ES import
#   import("modal") / await import('modal')      — dynamic ES import
modal_import_pattern=$'(from|require[[:space:]]*\\(|import)[[:space:]]*\\(?[[:space:]]*[\'"]modal[\'"]'
if (( ${#EXISTING_DIRS[@]} > 0 )); then
  if grep -RIn \
       --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --include='*.mjs' --include='*.cjs' \
       --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist \
       --exclude-dir=build \
       -E "$modal_import_pattern" \
       "${EXISTING_DIRS[@]}" 2>/dev/null; then
    fail "MODAL_SDK_IMPORT_IN_CLIENT: 'modal' SDK imported from public/client paths"
  else
    ok "no Modal SDK import found in client surfaces"
  fi
fi

# ── 3. Server-side relay must exist before agents are wired ──────────────────
if [[ -f .agents/pr_review.py ]]; then
  ok "server-side relay present (.agents/pr_review.py)"
else
  fail "RELAY_MISSING: .agents/pr_review.py not found"
fi

# ── 4. Router/validators packages are reachable ──────────────────────────────
for pkg in .agents/router/__init__.py .agents/validators/__init__.py; do
  if [[ -f "$pkg" ]]; then
    ok "package init present: $pkg"
  else
    warn "package init missing: $pkg"
  fi
done

# ── 5. Secrets boundary: presence reported, never echoed ─────────────────────
for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT AGENT_API_TOKEN; do
  if [[ -n "${!v:-}" ]]; then
    ok "$v=SET"
  else
    warn "SECRET_MISSING: $v (expected outside CI/runtime)"
  fi
done

# ── 6. Workflow uses `secrets.*` indirection (never hardcoded URLs) ──────────
WF=.github/workflows/agent-review.yml
if [[ -f "$WF" ]]; then
  if grep -E 'https?://[^[:space:]]*\.modal\.run' "$WF" >/dev/null 2>&1; then
    fail "WORKFLOW_HARDCODED_MODAL_URL: $WF"
  else
    ok "workflow $WF has no hardcoded modal URL"
  fi
else
  warn "workflow not found: $WF"
fi

if [[ "$status" == "PASS" ]]; then
  echo "[RESULT] PASS"
  exit 0
else
  echo "[RESULT] FAIL"
  exit 1
fi
