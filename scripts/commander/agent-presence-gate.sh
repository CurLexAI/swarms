#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE=".agents/config/agents.yaml"
WORKFLOW_FILE=".github/workflows/agent-review.yml"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[FAIL] CONFIG_NOT_FOUND: $CONFIG_FILE"
  exit 1
fi

if [[ ! -f "$WORKFLOW_FILE" ]]; then
  echo "[FAIL] CONFIG_NOT_FOUND: $WORKFLOW_FILE"
  exit 1
fi

echo "[INFO] Parsing configured agents from $CONFIG_FILE"
ruby - <<'RUBY'
require "yaml"
path = ".agents/config/agents.yaml"
data = YAML.load_file(path) || {}
agents = data.fetch("agents", {})
puts "[OK] configured_agent_count=#{agents.length}"
agents.each do |key,val|
  name = (val || {})["display_name"] || key
  model = ((val || {})["model"] || {})["id"] || "unknown"
  puts "[OK] agent=#{key} display_name=#{name} model=#{model}"
end
RUBY

echo "[INFO] Inspecting workflow gates in $WORKFLOW_FILE"
if rg -n "needs\.bayyinah-review\.outputs\.verdict == 'REQUEST_CHANGES'" "$WORKFLOW_FILE" >/dev/null; then
  echo "[OK] Mihwar is gated on Bayyinah REQUEST_CHANGES"
else
  echo "[WARN] Mihwar gate condition not found"
fi

if [[ -n "${BAYYINAH_ENDPOINT:-}" && -n "${AGENT_API_TOKEN:-}" ]]; then
  echo "[OK] BAYYINAH endpoint/token env vars present"
else
  echo "[WARN] SECRET_MISSING: BAYYINAH_ENDPOINT or AGENT_API_TOKEN"
fi

if [[ -n "${MIHWAR_ENDPOINT:-}" && -n "${AGENT_API_TOKEN:-}" ]]; then
  echo "[OK] MIHWAR endpoint/token env vars present"
else
  echo "[WARN] SECRET_MISSING: MIHWAR_ENDPOINT or AGENT_API_TOKEN"
fi

echo "[INFO] gate completed"
