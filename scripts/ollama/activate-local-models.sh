#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Activate and verify the sovereign local Ollama model set.
# This script never uses external AI APIs. Model downloads happen only when
# OLLAMA_PULL=1 is set explicitly by a human/operator on a local runtime.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST_PATH="${OLLAMA_MODEL_MANIFEST:-${REPO_ROOT}/config/ollama.local.models.json}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_PULL="${OLLAMA_PULL:-0}"
CURL_MAX_TIME="${OLLAMA_CURL_MAX_TIME:-10}"

info() { printf 'INFO: %s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
err() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_command() {
  command -v "$1" >/dev/null 2>&1 || err "$1 command is required."
}

require_local_ollama_url() {
  python3 - "$OLLAMA_BASE_URL" <<'PY'
from __future__ import annotations

import sys
from urllib.parse import urlparse

url = sys.argv[1]
parsed = urlparse(url)
allowed_hosts = {"localhost", "127.0.0.1", "::1", "ollama"}
if parsed.scheme not in {"http", "https"} or parsed.hostname not in allowed_hosts:
    raise SystemExit("OLLAMA_BASE_URL must point to localhost, loopback, or the internal Docker host 'ollama'.")
PY
}

read_manifest_models() {
  python3 - "$MANIFEST_PATH" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
models = data.get("models", [])
required_count = int(data.get("policy", {}).get("requiredModelCount", 18))
if len(models) != required_count:
    raise SystemExit(f"manifest must contain exactly {required_count} models, found {len(models)}")
seen_ids: set[str] = set()
seen_models: set[str] = set()
for item in models:
    model_id = str(item.get("id", "")).strip()
    model_name = str(item.get("model", "")).strip()
    required = item.get("required") is True
    if not model_id or not model_name or not required:
        raise SystemExit("every model requires non-empty id/model and required=true")
    if model_id in seen_ids:
        raise SystemExit(f"duplicate model id: {model_id}")
    if model_name in seen_models:
        raise SystemExit(f"duplicate model name: {model_name}")
    seen_ids.add(model_id)
    seen_models.add(model_name)
    print(model_name)
PY
}

query_installed_models() {
  local tags_json
  tags_json="$(curl -fsS --max-time "$CURL_MAX_TIME" "${OLLAMA_BASE_URL%/}/api/tags")"
  python3 - "$tags_json" <<'PY'
from __future__ import annotations

import json
import sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    raise SystemExit("Ollama /api/tags returned invalid JSON")
for item in data.get("models", []):
    name = str(item.get("name", "")).strip()
    if name:
        print(name)
PY
}

require_command python3
require_command curl
[ -f "$MANIFEST_PATH" ] || err "manifest not found: $MANIFEST_PATH"
require_local_ollama_url

mapfile -t required_models < <(read_manifest_models)
info "Sovereign Ollama manifest loaded: ${#required_models[@]} models."
info "Ollama base URL: ${OLLAMA_BASE_URL}"

if ! curl -fsS --max-time "$CURL_MAX_TIME" "${OLLAMA_BASE_URL%/}/api/tags" >/dev/null; then
  err "Ollama is not reachable. Start it locally first, for example: docker compose up -d ollama"
fi

mapfile -t installed_models < <(query_installed_models)
missing_models=()
for model in "${required_models[@]}"; do
  found=0
  for installed in "${installed_models[@]}"; do
    if [[ "$installed" == "$model" ]]; then
      found=1
      break
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    missing_models+=("$model")
  fi
done

if [[ "${#missing_models[@]}" -gt 0 && "$OLLAMA_PULL" == "1" ]]; then
  require_command ollama
  info "Pulling missing local Ollama models: ${#missing_models[@]}"
  for model in "${missing_models[@]}"; do
    info "ollama pull ${model}"
    ollama pull "$model"
  done
  mapfile -t installed_models < <(query_installed_models)
  missing_models=()
  for model in "${required_models[@]}"; do
    found=0
    for installed in "${installed_models[@]}"; do
      if [[ "$installed" == "$model" ]]; then
        found=1
        break
      fi
    done
    if [[ "$found" -eq 0 ]]; then
      missing_models+=("$model")
    fi
  done
fi

if [[ "${#missing_models[@]}" -gt 0 ]]; then
  warn "Missing local Ollama models: ${#missing_models[@]}"
  for model in "${missing_models[@]}"; do
    warn "missing: ${model}"
  done
  err "Local Ollama activation incomplete. Re-run with OLLAMA_PULL=1 on the local model host."
fi

info "VERIFIED: all ${#required_models[@]} sovereign local Ollama models are installed."
