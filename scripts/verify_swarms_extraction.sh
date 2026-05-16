#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="${1:-.}"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

pass() {
  printf 'PASS: %s\n' "$1"
}

require_file() {
  local file_path="$1"
  if [[ ! -f "$ROOT_DIR/$file_path" ]]; then
    fail "missing required file: $file_path"
  fi
}

require_dir() {
  local dir_path="$1"
  if [[ ! -d "$ROOT_DIR/$dir_path" ]]; then
    fail "missing required directory: $dir_path"
  fi
}

if [[ ! -d "$ROOT_DIR" ]]; then
  fail "root directory does not exist: $ROOT_DIR"
fi

if [[ -f "$ROOT_DIR/LexPrim-main.zip" ]]; then
  fail "archive artifact LexPrim-main.zip must not remain in repository root"
fi

require_file "AGENTS.md"
require_file "README.md"
require_file "package.json"
require_file ".agents/config/agents.yaml"
require_file "src/services/unifiedAgentAdapter.ts"
require_dir ".agents"
require_dir "scripts"
require_dir "tests"

if [[ -f "$ROOT_DIR/agents/registry.yaml" ]]; then
  fail "legacy agents/registry.yaml is present; unified adapter must use .agents/config/agents.yaml"
fi

if command -v git >/dev/null 2>&1 && [[ -d "$ROOT_DIR/.git" ]]; then
  changed_files="$(git -C "$ROOT_DIR" status --short --untracked-files=all || true)"
  if printf '%s\n' "$changed_files" | grep -E '(^|[[:space:]])(node_modules/|dist/|coverage/|\.env$)' >/dev/null; then
    fail "working tree contains prohibited generated or secret-like files"
  fi
fi

if command -v find >/dev/null 2>&1; then
  if find "$ROOT_DIR" \( -path "$ROOT_DIR/.git" -o -path "$ROOT_DIR/node_modules" -o -path "$ROOT_DIR/dist" -o -path "$ROOT_DIR/coverage" \) -prune -o -type f -name '*.zip' -print | grep -q .; then
    fail "zip artifacts are not allowed in extracted repository content"
  fi
fi

pass "swarms extraction structure is executable and canonical"
