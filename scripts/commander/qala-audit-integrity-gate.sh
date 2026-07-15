#!/usr/bin/env bash
# Qal'a Q7 — Sealed Audit Integrity Gate
#
# Verifies that the on-disk, append-only audit chain has not been
# tampered with. Wraps QalaAuditSink.verify_chain (the existing engine
# in .agents/validators/qala_audit_sink.py) — it does NOT re-implement
# the chain logic.
#
# Fail posture:
#   - A *present but broken* chain FAILs the gate (fail-closed): a
#     tampered, inserted, truncated, or gapped record is a hard error.
#   - An *absent or empty* log PASSes: lazily-created sinks have no
#     records before first append, which is the normal pre-activation
#     state and must not wedge CI.
#   - A python3 or I/O runtime failure FAILs the gate (fail-closed).
#
# Sink path resolution (delegated to the verifier CLI):
#   $QALA_AUDIT_SINK_PATH, else artifacts/security/qala-audit.jsonl.
#
# Generated-artifact model (ADR-0008 §Decision.4): the sealed chain is NOT
# tracked in git. When the merge-safe event source
# (artifacts/security/qala-audit.events.json) is present, this gate first
# deterministically *seals* it into the chain, then verifies it. Verification
# enforces the committed anchor (artifacts/security/qala-audit.anchor.json:
# recordCount + headHash) so tail truncation is detected — forward link-walking
# alone cannot catch removal of the last N records.
#
# See .agents/validators/qala_audit_sink.py and
# docs/decisions/ADR-0003-qala-security-architecture.md §Q7.

set -euo pipefail

ROOT_DIR="${1:-.}"
cd "$ROOT_DIR"

status="PASS"
ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; status="FAIL"; }
info() { echo "[INFO] $*"; }
require_repo_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    fail "REPO_FILE_MISSING: $file not found"
    echo "[RESULT] FAIL"
    exit 1
  fi
}

info "Qal'a audit integrity gate (Q7)"
REPO_DIR="$(pwd)"
require_repo_file "src/security/qalaAuditSink.ts"
require_repo_file ".agents/validators/qala_audit_sink.py"
require_repo_file "tests/qalaAuditSink.test.js"
require_repo_file "tests/test_qala_audit_sink.py"
info "repo=$REPO_DIR"

VERIFIER="$REPO_DIR/.agents/validators/qala_audit_sink.py"

if [[ ! -f "$VERIFIER" ]]; then
  fail "VERIFIER_MISSING: $VERIFIER not found"
  echo "[RESULT] FAIL"
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  fail "PYTHON3_MISSING: cannot run audit chain verifier"
  echo "[RESULT] FAIL"
  exit 1
fi

# Canonically validate configured paths early to prevent any escape or path traversal.
# This runs the verifier's own path-confinement checks, which will raise ValueError
# for any out-of-bound, relative-escaping, or absolute paths outside artifacts/security.
info "validating paths against artifacts/security"
if ! python3 -c "
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.join('$REPO_DIR', '.agents', 'validators'))
import qala_audit_sink
try:
    # Resolve and validate each path. If they escape, _confine_cli_path raises ValueError.
    qala_audit_sink._resolve_events_path(os.environ.get('QALA_AUDIT_EVENTS_PATH'))
    qala_audit_sink._resolve_verify_path(os.environ.get('QALA_AUDIT_SINK_PATH'))
    qala_audit_sink._resolve_anchor_path(os.environ.get('QALA_AUDIT_ANCHOR_PATH'))
except ValueError as e:
    print(f'PATH_VALIDATION_FAILED: {e}')
    sys.exit(2)
"; then
  fail "PATH_VALIDATION_FAILED: one or more paths are invalid or escape artifacts/security"
  echo "[RESULT] FAIL"
  exit 1
fi

# Generated-artifact model: seal the chain from the merge-safe event source
# before verifying. Skipped when no event source exists (pre-activation), which
# preserves the "absent log PASSes" posture above.
EVENTS_PATH="${QALA_AUDIT_EVENTS_PATH:-artifacts/security/qala-audit.events.json}"
if [[ "$EVENTS_PATH" = /* ]]; then
  fail "EVENT_SOURCE_OUTSIDE_AUDIT_WORKDIR: absolute event path rejected: $EVENTS_PATH"
  echo "[RESULT] FAIL"
  exit 1
fi
if [[ -f "$EVENTS_PATH" ]]; then
  info "sealing audit chain from event source: $EVENTS_PATH"
  set +e
  seal_output="$(python3 "$VERIFIER" seal)"
  seal_rc=$?
  set -e
  printf '%s\n' "$seal_output"
  if [[ "$seal_rc" -ne 0 ]]; then
    fail "AUDIT_SEAL_FAILED: could not seal chain from $EVENTS_PATH (rc=$seal_rc)"
    echo "[RESULT] FAIL"
    exit 1
  fi
else
  info "no event source at $EVENTS_PATH; verifying any existing chain as-is"
fi

# Verifier exit codes:
#   0  -> chain intact (or empty/absent log) — gate PASSes
#   10 -> AUDIT_CHAIN_BROKEN — gate FAILs
#   2+ -> runtime/read failure — gate FAILs (fail-closed)
set +e
verify_output="$(python3 "$VERIFIER" verify)"
py_rc=$?
set -e

printf '%s\n' "$verify_output"

case "$py_rc" in
  0)
    ok "audit chain intact"
    ;;
  10)
    fail "AUDIT_CHAIN_BROKEN: the sealed audit chain failed verification"
    ;;
  *)
    fail "VERIFIER_ERROR: audit chain verifier exited rc=$py_rc"
    ;;
esac

if [[ "$status" == "PASS" ]]; then
  echo "[RESULT] PASS"
  exit 0
fi
echo "[RESULT] FAIL"
exit 1
