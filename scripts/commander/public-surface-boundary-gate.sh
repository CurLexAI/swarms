#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

status="PASS"
ok()   { echo "[OK]   $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
info() { echo "[INFO] $*"; }

info "Public surface boundary gate"

[[ -d public ]] || { ok "public/ not present"; exit 0; }

mapfile -t public_entries < <(find public -mindepth 1 -maxdepth 1 -printf '%P\n' | sort)
allowed=("control" "index.html" "trust")

declare -A allowed_map=()
for a in "${allowed[@]}"; do
  allowed_map["$a"]=1
done

for entry in "${public_entries[@]}"; do
  if [[ -z "${allowed_map[$entry]:-}" ]]; then
    fail "UNAPPROVED_PUBLIC_SURFACE: public/$entry"
  fi
done

if [[ "$status" == "FAIL" ]]; then
  marker="${ADR_APPROVAL_MARKER:-}"
  if [[ "$marker" =~ ^ADR-000[0-9]+$ ]] && [[ -f "docs/decisions/${marker}"* ]]; then
    ok "ADR override marker accepted via ADR_APPROVAL_MARKER=$marker"
    status="PASS"
  else
    fail "ADR_APPROVAL_REQUIRED: set ADR_APPROVAL_MARKER=ADR-XXXX and add matching accepted ADR"
  fi
fi

if [[ "$status" == "PASS" ]]; then
  echo "[RESULT] PASS"
  exit 0
fi

echo "[RESULT] FAIL"
exit 1
