#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

status="PASS"
ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
info() { echo "[INFO] $*"; }

info "ADR-0001 boundary gate"
info "repo=$(pwd)"

# public/control is allowed per ADR-0002 (operator-only static artifacts boundary).
# public/trust is allowed per ADR-0002. public/index.html remains forbidden.
FORBIDDEN_PATHS=(
  "backend_fastapi"
  "src/routes"
  "src/pipeline"
  "src/factory"
  "src/control-hub"
  "src/api"
  "src/apiSecurity.js"
  "public/index.html"
  "public/about"
  "public/contact"
  "public/privacy"
  "public/terms"
)

for path in "${FORBIDDEN_PATHS[@]}"; do
  if [[ -e "$path" ]]; then
    fail "BOUNDARY_DRIFT: forbidden path present: $path"
  fi
done

SCAN_DIRS=(.agents agents src public .github)
EXISTING_SCAN_DIRS=()
for d in "${SCAN_DIRS[@]}"; do
  [[ -e "$d" ]] && EXISTING_SCAN_DIRS+=("$d")
done

if (( ${#EXISTING_SCAN_DIRS[@]} == 0 )); then
  warn "no boundary-relevant directories found to scan"
else
  if rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' '\bautoStart\b' "${EXISTING_SCAN_DIRS[@]}" >/dev/null 2>&1; then
    fail "BOUNDARY_DRIFT: autoStart activation flag detected"
  else
    ok "no autoStart activation flag detected"
  fi
fi

if [[ "$status" == "PASS" ]]; then
  echo "[RESULT] PASS"
  exit 0
else
  echo "[RESULT] FAIL"
  exit 1
fi
