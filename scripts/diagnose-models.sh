#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# diagnose-models.sh — Runtime model availability diagnostic
# Reports which model runtimes are reachable from this environment.
# No secrets are printed. Exit 0 always (diagnostic, not gate).

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

ok()   { printf "  ${GREEN}✓${RESET} %s\n" "$1"; }
fail() { printf "  ${RED}✗${RESET} %s\n" "$1"; }
warn() { printf "  ${YELLOW}⚠${RESET} %s\n" "$1"; }
section() { printf "\n${BOLD}── %s${RESET}\n" "$1"; }

section "1. Modal CLI"
if command -v modal &>/dev/null; then
  ok "modal CLI installed: $(modal --version 2>&1 | head -1)"
else
  fail "modal CLI not found"
fi

section "2. Modal Secrets (presence only)"
for var in MODAL_TOKEN_ID MODAL_TOKEN_SECRET; do
  if [ -n "${!var:-}" ]; then
    ok "$var is SET"
  else
    fail "$var is UNSET"
  fi
done

section "3. Agent Endpoint Secrets (presence only)"
for var in MIHWAR_ENDPOINT BAYYINAH_ENDPOINT MIHWAR_API_TOKEN BAYYINAH_API_TOKEN; do
  if [ -n "${!var:-}" ]; then
    ok "$var is SET"
  else
    fail "$var is UNSET"
  fi
done

section "4. Local Ollama (localhost:11434)"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
if curl -sf --max-time 3 "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
  ok "Ollama responding at ${OLLAMA_URL}"
  MODELS=$(curl -sf --max-time 5 "${OLLAMA_URL}/api/tags" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for m in data.get('models', []):
        print('    - ' + m.get('name', '?'))
except Exception:
    pass
" 2>/dev/null || true)
  if [ -n "$MODELS" ]; then
    printf "  Available models:\n%s\n" "$MODELS"
  else
    warn "No models pulled yet (run: ollama pull qwen2.5-coder:32b)"
  fi
else
  fail "Ollama not responding at ${OLLAMA_URL}"
fi

section "5. LM Studio / OpenAI-compatible (localhost:1234)"
LM_URL="${LM_STUDIO_URL:-http://localhost:1234}"
if curl -sf --max-time 3 "${LM_URL}/v1/models" >/dev/null 2>&1; then
  ok "OpenAI-compatible server responding at ${LM_URL}"
else
  fail "No OpenAI-compatible server at ${LM_URL}"
fi

section "6. vLLM / Inference Server (localhost:8000)"
VLLM_URL="${VLLM_URL:-http://localhost:8000}"
if curl -sf --max-time 3 "${VLLM_URL}/v1/models" >/dev/null 2>&1; then
  ok "vLLM/inference server responding at ${VLLM_URL}"
else
  fail "No vLLM/inference server at ${VLLM_URL}"
fi

section "7. Python packages"
for pkg in modal ollama openai vllm transformers; do
  if python3 -c "import ${pkg}" 2>/dev/null; then
    ok "${pkg} importable"
  else
    fail "${pkg} not installed"
  fi
done

section "8. Agent config"
AGENTS_YAML=".agents/config/agents.yaml"
if [ -f "$AGENTS_YAML" ]; then
  ok "agents.yaml exists"
else
  fail "agents.yaml missing"
fi

section "9. Routing policy summary"
printf "  Coding/Review tasks → Modal vLLM (Mihwar/Bayyinah)\n"
printf "  Critical/Arabic-legal → Anthropic + Bayyinah review\n"
printf "  Fast draft/low-risk  → OpenAI\n"
printf "  Offline fallback     → Ollama (localhost)\n"

printf "\n${BOLD}── Diagnostic complete${RESET}\n"
exit 0
