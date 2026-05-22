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
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[FAIL] python3/python not found"
  exit 1
fi
"$PY" - <<'PY'
import yaml

path = ".agents/config/agents.yaml"
with open(path, encoding="utf-8") as handle:
    data = yaml.safe_load(handle) or {}
agents = data.get("agents", {})
print(f"[OK] configured_agent_count={len(agents)}")
for key, val in agents.items():
    val = val or {}
    name = val.get("display_name") or key
    model = (val.get("model") or {}).get("id") or "unknown"
    print(f"[OK] agent={key} display_name={name} model={model}")
PY

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
