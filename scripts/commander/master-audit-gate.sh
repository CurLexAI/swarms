#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

failures=0
warnings=0

ok()   { echo "[OK]   $*"; }
info() { echo "[INFO] $*"; }
warn() { echo "[WARN] $*"; warnings=$((warnings + 1)); }
fail() { echo "[FAIL] $*"; failures=$((failures + 1)); }

lower() {
  printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]'
}

bool_is_true() {
  case "$(lower "${1:-}")" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

sanitize_origin() {
  python3 - "$1" <<'PY'
from __future__ import annotations

import sys
from urllib.parse import urlsplit

value = sys.argv[1]
parts = urlsplit(value)
if not parts.scheme or not parts.hostname:
    print("UNPARSEABLE")
    raise SystemExit(0)
port = f":{parts.port}" if parts.port else ""
print(f"{parts.scheme}://{parts.hostname}{port}")
PY
}

probe_path_for() {
  local endpoint="$1"
  local origin
  origin="$(sanitize_origin "$endpoint")"
  if [[ "$origin" =~ :11434$ ]]; then
    printf '%s/api/tags' "$origin"
  else
    printf '%s' "$endpoint"
  fi
}

require_file() {
  local path="$1"
  if [[ -f "$path" ]]; then
    ok "file present: $path"
  else
    fail "FILE_MISSING: $path"
  fi
}

require_pattern() {
  local label="$1"
  local pattern="$2"
  local path="$3"
  if grep -F "$pattern" "$path" >/dev/null 2>&1; then
    ok "$label"
  else
    fail "$label"
  fi
}

run_gate() {
  local label="$1"
  local path="$2"
  if [[ ! -f "$path" ]]; then
    warn "GATE_MISSING: $path"
    return
  fi
  if bash "$path" .; then
    ok "$label passed"
  else
    fail "$label failed"
  fi
}

probe_endpoint() {
  local name="$1"
  local endpoint="$2"
  local strict="$3"
  local origin probe_url

  origin="$(sanitize_origin "$endpoint")"
  if [[ "$origin" == "UNPARSEABLE" ]]; then
    if bool_is_true "$strict"; then
      fail "${name}_ENDPOINT_INVALID: could not parse endpoint"
    else
      warn "${name}_ENDPOINT_INVALID: could not parse endpoint"
    fi
    return
  fi

  if ! command -v curl >/dev/null 2>&1; then
    if bool_is_true "$strict"; then
      fail "CURL_MISSING: cannot probe ${name} endpoint"
    else
      warn "CURL_MISSING: skipped ${name} endpoint probe"
    fi
    return
  fi

  probe_url="$(probe_path_for "$endpoint")"
  if curl -fsS --connect-timeout 2 --max-time 5 "$probe_url" >/dev/null 2>&1; then
    ok "${name} endpoint reachable: ${origin}"
    return
  fi

  if bool_is_true "$strict"; then
    fail "${name}_ENDPOINT_UNREACHABLE: ${origin}"
  else
    warn "${name}_ENDPOINT_UNREACHABLE: ${origin}"
  fi
}

echo "================================================================="
echo "Master Audit Gate — architecture, MCP, agents, and sovereignty"
echo "repo=$(pwd)"
echo "================================================================="

echo
info "[1/6] Existing boundary gates"
run_gate "ADR-0001 boundary gate" "scripts/commander/adr-0001-boundary-gate.sh"
run_gate "Modal boundary gate" "scripts/commander/modal-boundary-gate.sh"

echo
info "[2/6] Sovereign endpoint posture"
STRICT_ENDPOINTS="${MASTER_AUDIT_REQUIRE_ENDPOINTS:-false}"
MIHWAR_URL="${MIHWAR_ENDPOINT:-http://localhost:11434}"
BAYYINAH_URL="${BAYYINAH_ENDPOINT:-http://localhost:11434}"
info "MASTER_AUDIT_REQUIRE_ENDPOINTS=$(lower "$STRICT_ENDPOINTS")"
probe_endpoint "MIHWAR" "$MIHWAR_URL" "$STRICT_ENDPOINTS"
probe_endpoint "BAYYINAH" "$BAYYINAH_URL" "$STRICT_ENDPOINTS"

echo
info "[3/6] MCP integration"
require_file ".agents/mcp/server.py"
require_file ".agents/mcp/README.md"
require_file ".agents/mcp/copilot-mcp-config.json"
require_pattern "MCP server exports mihwar_generate" '"name": "mihwar_generate"' ".agents/mcp/server.py"
require_pattern "MCP server exports bayyinah_review" '"name": "bayyinah_review"' ".agents/mcp/server.py"
require_pattern "MCP README documents mihwar_generate" '`mihwar_generate`' ".agents/mcp/README.md"
require_pattern "MCP README documents bayyinah_review" '`bayyinah_review`' ".agents/mcp/README.md"
if grep -F '"mcpServers"' .agents/mcp/copilot-mcp-config.json .github/copilot/mcp.json >/dev/null 2>&1; then
  ok "mcpServers configuration present"
else
  warn "MCP_CONFIG_MISSING: no mcpServers block found in expected config files"
fi

echo
info "[4/6] Architecture doctrine and registry"
require_file "AGENTS.md"
require_file "CLAUDE.md"
require_file "ARCHITECTURE_DIRECTIVE.md"
require_file "docs/decisions/ADR-0001-swarms-boundary.md"
require_file ".agents/config/agents.yaml"
if [[ -f ".agents/catalog/agents.yaml" ]]; then
  ok "file present: .agents/catalog/agents.yaml"
else
  warn "OPTIONAL_FILE_MISSING: .agents/catalog/agents.yaml"
fi
if [[ -f "agents/registry.yaml" ]]; then
  ok "file present: agents/registry.yaml"
else
  warn "OPTIONAL_FILE_MISSING: agents/registry.yaml"
fi

echo
info "[5/6] Security posture, Aegis, and Qal'a"
require_file ".agents/mcp/aegis_gateway.py"
require_file ".agents/validators/qala_input_gate.py"
require_file ".agents/validators/qala_trace.py"
require_file ".agents/validators/qala_audit_sink.py"
require_file ".agents/validators/qala_ksa_pii.py"
if [[ -n "${QALA_AUDIT_SINK_PATH:-}" ]]; then
  ok "QALA_AUDIT_SINK_PATH=SET"
elif grep -F 'artifacts/security/qala-audit.jsonl' .agents/validators/qala_audit_sink.py >/dev/null 2>&1; then
  ok "Qal'a audit sink default path documented in verifier"
else
  fail "AUDIT_SINK_DEFAULT_MISSING: QALA_AUDIT_SINK_PATH unset and no default sink path found"
fi
if bool_is_true "${ALLOW_EXTERNAL_AI:-false}"; then
  fail "ALLOW_EXTERNAL_AI=true"
else
  ok "ALLOW_EXTERNAL_AI is not enabled"
fi
if grep -F 'ALLOW_EXTERNAL_AI' .agents/providers/openai_provider.py >/dev/null 2>&1 \
  && grep -F 'ALLOW_EXTERNAL_AI' .agents/providers/anthropic_provider.py >/dev/null 2>&1; then
  ok "external provider adapters are fail-closed behind ALLOW_EXTERNAL_AI"
else
  warn "EXTERNAL_PROVIDER_GUARD_UNVERIFIED: provider ALLOW_EXTERNAL_AI guard not confirmed"
fi

echo
info "[6/6] Qarar / Bayyinah boundary"
require_pattern \
  "Architecture directive forbids direct Qarar -> Bayyinah access" \
  "Qarar لا يتصل مباشرةً بـ Bayyinah." \
  "ARCHITECTURE_DIRECTIVE.md"
require_pattern \
  "Architecture directive routes Qarar / Bayyinah traffic through Mihwar" \
  "كل تفاعل بين Qarar وBayyinah يمر حصراً عبر Mihwar." \
  "ARCHITECTURE_DIRECTIVE.md"
PUBLIC_SURFACE_DIRS=(public app pages components)
EXISTING_PUBLIC_SURFACE_DIRS=()
for dir in "${PUBLIC_SURFACE_DIRS[@]}"; do
  [[ -d "$dir" ]] && EXISTING_PUBLIC_SURFACE_DIRS+=("$dir")
done
if (( ${#EXISTING_PUBLIC_SURFACE_DIRS[@]} == 0 )); then
  warn "PUBLIC_SURFACE_SCAN_SKIPPED: no public/client directories found"
elif grep -RIn \
  --exclude-dir=.git --exclude-dir=node_modules \
  -E 'direct_bayyinah_connect|BAYYINAH_ENDPOINT|bayyinah_review_web|BayyinahAgent' \
  "${EXISTING_PUBLIC_SURFACE_DIRS[@]}" 2>/dev/null; then
  fail "QARAR_BAYYINAH_BYPASS_REFERENCE: public/client surface references Bayyinah directly"
else
  ok "no direct Bayyinah reference detected in public/client surfaces"
fi

echo
echo "================================================================="
if (( failures > 0 )); then
  echo "[RESULT] FAIL failures=${failures} warnings=${warnings}"
  exit 1
fi
echo "[RESULT] PASS failures=0 warnings=${warnings}"
exit 0
