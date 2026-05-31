#!/usr/bin/env bash
set -euo pipefail

# Read-only diagnostic for iPhone <-> remote SSH connectivity and repo sync state.
# No secrets are printed and no remote changes are performed.

HOST="${1:-}"
PORT="${2:-22}"
USER_NAME="${3:-}"

print_header() {
  printf '\n== %s ==\n' "$1"
}

safe_run() {
  local label="$1"
  shift
  printf '[CHECK] %s\n' "$label"
  if "$@"; then
    printf '[PASS] %s\n' "$label"
  else
    printf '[FAIL] %s\n' "$label"
  fi
}

print_header "Local repository identity"
safe_run "git remote -v" git remote -v
safe_run "git branch --show-current" git branch --show-current
safe_run "git status --short" git status --short

print_header "Local runtime checks"
safe_run "Python agent syntax" python3 -m py_compile .agents/modal_app.py .agents/invoke.py .agents/pr_review.py
safe_run "Agent inventory" python3 .agents/invoke.py info

print_header "SSH target checks"
if [[ -z "$HOST" || -z "$USER_NAME" ]]; then
  printf '[WARN] Host/user not provided. Usage: %s <host> [port] <user>\n' "$0"
  printf '[INFO] Skipping remote SSH probe.\n'
  exit 0
fi

safe_run "DNS/IP resolution" getent hosts "$HOST"

if command -v nc >/dev/null 2>&1; then
  safe_run "TCP port reachable" nc -zv "$HOST" "$PORT"
else
  printf '[WARN] nc not installed; skipping TCP probe.\n'
fi

SSH_OPTS=(
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=7
  -p "$PORT"
)

safe_run "SSH handshake" ssh "${SSH_OPTS[@]}" "${USER_NAME}@${HOST}" "echo connected"

print_header "Remote repository and service state"
safe_run "Remote git + sshd status" ssh "${SSH_OPTS[@]}" "${USER_NAME}@${HOST}" '
  set -euo pipefail
  cd ~/swarms
  git remote -v
  git branch --show-current
  git status --short
  if command -v systemctl >/dev/null 2>&1; then
    systemctl is-active ssh || systemctl is-active sshd || true
  fi
'

print_header "Result"
printf '[DONE] Diagnostic completed. Use PASS/FAIL signals to resolve iPhone sync blockers.\n'
