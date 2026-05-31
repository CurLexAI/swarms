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
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "[FAIL] PYTHON_NOT_FOUND: python3 or python is required"
    exit 1
  fi
fi

"$PYTHON_BIN" - <<'PY'
import importlib.util
from pathlib import Path

invoke_path = Path(".agents/invoke.py")
spec = importlib.util.spec_from_file_location("agent_invoke", invoke_path)
if spec is None or spec.loader is None:
    raise SystemExit(f"[FAIL] CONFIG_PARSE_FAILURE: could not load {invoke_path}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
data = module.load_config() or {}
agents = data.get("agents", {})
print(f"[OK] configured_agent_count={len(agents)}")
for key, val in agents.items():
    agent = val or {}
    name = agent.get("display_name") or key
    model = (agent.get("model") or {}).get("id") or "unknown"
    print(f"[OK] agent={key} display_name={name} model={model}")
PY

echo "[INFO] Inspecting workflow gates in $WORKFLOW_FILE"
if grep -E -n "needs\.bayyinah-review\.outputs\.verdict == 'REQUEST_CHANGES'" "$WORKFLOW_FILE" >/dev/null; then
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
