#!/usr/bin/env bash
set -euo pipefail

repo="${1:-.}"
cd "$repo"

status="PASS"
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
ok() { echo "[OK] $*"; }
info() { echo "[INFO] $*"; }

info "Codex Commander gate"
info "repo=$(pwd)"

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ok "git repository detected"
  git branch --show-current | sed 's/^/[INFO] branch=/'
  git rev-parse HEAD | sed 's/^/[INFO] head=/'
else
  fail "not a git repository"
fi

if [ -f AGENTS.md ]; then
  ok "AGENTS.md present"
else
  warn "AGENTS.md missing"
fi

if [ -f .agents/config/agents.yaml ]; then
  ok ".agents/config/agents.yaml present"
elif [ -f agents/registry.yaml ]; then
  ok "agents/registry.yaml present"
else
  warn "agent registry not found"
fi

if find . -path './.github/agents/*.agent.md' -type f | grep -q .; then
  ok "GitHub Copilot custom agent profiles present"
else
  warn "no .github/agents/*.agent.md profiles found"
fi

if grep -RIn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.next --exclude-dir=dist --exclude-dir=build '\.modal\.run' src public app pages components 2>/dev/null; then
  fail "direct Modal URL reference found in public/client paths"
else
  ok "no direct Modal URL reference found in common public/client paths"
fi

if [ -f package.json ]; then
  ok "package.json present"
else
  warn "package.json missing; npm tests/audit are NOT_APPLICABLE"
fi

for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN; do
  if [ -n "${!v:-}" ]; then
    ok "$v=SET"
  else
    warn "$v=UNSET"
  fi
done

if [ "$status" = "PASS" ]; then
  echo "[RESULT] PASS"
else
  echo "[RESULT] FAIL"
  exit 1
fi
