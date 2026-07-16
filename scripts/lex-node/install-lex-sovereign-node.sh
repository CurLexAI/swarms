#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
STATE_DIR="/var/lib/lex-sovereign-node"
REGISTRY=""
APPLY=false
usage(){ echo "Usage: $0 --registry FILE [--state-dir DIR] [--apply] (FILE must reside under the invoking directory or /var/lib/lex-sovereign-node)" >&2; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY="${2:?}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:?}"; shift 2 ;;
    --apply) APPLY=true; shift ;;
    *) usage; exit 64 ;;
  esac
done
[[ -n "$REGISTRY" && -f "$REGISTRY" ]] || { usage; exit 64; }
if [[ "$APPLY" != true ]]; then
  python3 "$(dirname "$0")/verify_registry.py" "$REGISTRY"
  echo "Validated registry $REGISTRY"
  echo "Would create root-owned state directory: $STATE_DIR"
  echo "Dry run complete. Re-run with --apply after approval."
  exit 0
fi
case "$STATE_DIR" in /var/lib/lex-sovereign-node|/var/lib/lex-sovereign-node/*) ;; *) echo "unsafe state directory" >&2; exit 65;; esac
install -d -m 0700 -o root -g root "$STATE_DIR"
# TOCTOU defense: copy the operator's registry ONCE into a root-owned
# staging file inside the state directory, validate that exact copy, then
# atomically rename it into place. The original path is never reopened
# after validation, so swapping the source file or a path component
# between validation and install has no effect.
STAGING="$(mktemp --suffix=.json "$STATE_DIR/registry.staging.XXXXXX")"
trap 'rm -f "$STAGING"' EXIT
install -m 0600 -o root -g root "$REGISTRY" "$STAGING"
python3 "$(dirname "$0")/verify_registry.py" "$STAGING"
echo "Validated staged registry copy"
mv -f "$STAGING" "$STATE_DIR/registry.json"
trap - EXIT
echo "Installation complete. Network enrollment and transport remain operator-managed."
