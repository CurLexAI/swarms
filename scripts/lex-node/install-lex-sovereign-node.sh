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
# Enforce the documented registry-source boundary (working directory or
# the state root) on the PATH ONLY — the source content is never read
# here, so there is no approve-then-swap window on the source file.
python3 "$(dirname "$0")/verify_registry.py" --confine-only "$REGISTRY"
echo "Confirmed registry source path boundary for $REGISTRY"
# Canonicalize before the allowlist check so ../ segments cannot escape
# the permitted state root.
STATE_DIR="$(realpath -m -- "$STATE_DIR")"
case "$STATE_DIR" in /var/lib/lex-sovereign-node|/var/lib/lex-sovereign-node/*) ;; *) echo "unsafe state directory" >&2; exit 65;; esac
install -d -m 0700 -o root -g root "$STATE_DIR"
# TOCTOU defense: the source is read exactly ONCE — copied into a
# root-owned staging file inside the state directory. Content validation
# and the atomic rename both operate on that immutable snapshot only, so
# no source swap can change what was validated versus what is installed.
STAGING="$(mktemp --suffix=.json "$STATE_DIR/registry.staging.XXXXXX")"
trap 'rm -f "$STAGING"' EXIT
install -m 0600 -o root -g root "$REGISTRY" "$STAGING"
python3 "$(dirname "$0")/verify_registry.py" "$STAGING"
echo "Validated staged registry snapshot"
mv -f "$STAGING" "$STATE_DIR/registry.json"
trap - EXIT
echo "Installation complete. Network enrollment and transport remain operator-managed."
