#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
STATE_DIR="/var/lib/lex-sovereign-node"
REGISTRY=""
APPLY=false
usage(){ echo "Usage: $0 --registry FILE [--state-dir DIR] [--apply]" >&2; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY="${2:?}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:?}"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    *) usage; exit 64 ;;
  esac
done
[[ -n "$REGISTRY" && -f "$REGISTRY" ]] || { usage; exit 64; }
python3 "$(dirname "$0")/verify_registry.py" "$REGISTRY"
echo "Validated registry $REGISTRY"
echo "Would create root-owned state directory: $STATE_DIR"
if [[ "$APPLY" != true ]]; then echo "Dry run complete. Re-run with --apply after approval."; exit 0; fi
case "$STATE_DIR" in /var/lib/lex-sovereign-node|/var/lib/lex-sovereign-node/*) ;; *) echo "unsafe state directory" >&2; exit 65;; esac
install -d -m 0700 -o root -g root "$STATE_DIR"
install -m 0600 -o root -g root "$REGISTRY" "$STATE_DIR/registry.json"
echo "Installation complete. Network enrollment and transport remain operator-managed."
