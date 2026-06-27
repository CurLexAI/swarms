#!/usr/bin/env bash
set -euo pipefail

GITHUB_REPO="${GITHUB_REPO:-CurLexAI/swarms}"
MIHWAR_HF_MODEL_ID="${MIHWAR_HF_MODEL_ID:-deepseek-ai/DeepSeek-Coder-V2-Instruct}"
BAYYINAH_HF_MODEL_ID="${BAYYINAH_HF_MODEL_ID:-Qwen/Qwen2.5-Coder-32B-Instruct}"

err() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "INFO: $*"; }

command -v gh >/dev/null 2>&1 || err "gh CLI not found. Install gh and run gh auth login."

if ! gh auth status >/dev/null 2>&1; then
  err "gh is not authenticated. Run gh auth login first."
fi

if [[ -z "${HF_TOKEN:-}" ]]; then
  read -r -s -p "Enter HF_TOKEN (input hidden): " HF_TOKEN
  echo
fi

[[ -n "${HF_TOKEN:-}" ]] || err "HF_TOKEN is required."

info "Writing HF_TOKEN to GitHub Secrets for ${GITHUB_REPO}."
printf '%s' "$HF_TOKEN" | gh secret set HF_TOKEN --repo "$GITHUB_REPO" --body-file - >/dev/null

info "Writing non-secret Hugging Face model configuration to GitHub Variables."
gh variable set HF_INTEGRATION_MODE --repo "$GITHUB_REPO" --body "inference_providers" >/dev/null
gh variable set HF_INFERENCE_BASE_URL --repo "$GITHUB_REPO" --body "https://router.huggingface.co/v1" >/dev/null
gh variable set MIHWAR_HF_MODEL_ID --repo "$GITHUB_REPO" --body "$MIHWAR_HF_MODEL_ID" >/dev/null
gh variable set BAYYINAH_HF_MODEL_ID --repo "$GITHUB_REPO" --body "$BAYYINAH_HF_MODEL_ID" >/dev/null

if [[ -n "${MIHWAR_HF_PROVIDER:-}" ]]; then
  gh variable set MIHWAR_HF_PROVIDER --repo "$GITHUB_REPO" --body "$MIHWAR_HF_PROVIDER" >/dev/null
fi
if [[ -n "${BAYYINAH_HF_PROVIDER:-}" ]]; then
  gh variable set BAYYINAH_HF_PROVIDER --repo "$GITHUB_REPO" --body "$BAYYINAH_HF_PROVIDER" >/dev/null
fi

info "Done. HF_TOKEN was not printed."
