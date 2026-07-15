#!/usr/bin/env bash
set -Eeuo pipefail
STATE_DIR="/var/lib/lex-sovereign-node"
CONFIRM=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --state-dir) STATE_DIR="${2:?}"; shift 2 ;;
    --confirm) CONFIRM=true; shift ;;
    *) echo "Usage: $0 [--state-dir DIR] --confirm" >&2; exit 64 ;;
  esac
done
[[ "$CONFIRM" == true ]] || { echo "Rollback requires --confirm" >&2; exit 64; }
case "$STATE_DIR" in /var/lib/lex-sovereign-node|/var/lib/lex-sovereign-node/*) ;; *) echo "unsafe state directory" >&2; exit 65;; esac
[[ -e "$STATE_DIR" ]] && rm -rf -- "$STATE_DIR"
echo "Local Lex Sovereign Node state removed. Revoke remote authorization separately."
