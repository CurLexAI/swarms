#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

if [[ ! -f "src/security/qalaAuditSink.ts" ]]; then
  echo "[qala-audit-integrity-gate] FAIL: src/security/qalaAuditSink.ts missing" >&2
  exit 1
fi

if [[ ! -f ".agents/validators/qala_audit_sink.py" ]]; then
  echo "[qala-audit-integrity-gate] FAIL: .agents/validators/qala_audit_sink.py missing" >&2
  exit 1
fi

if [[ ! -f "tests/qalaAuditSink.test.js" ]]; then
  echo "[qala-audit-integrity-gate] FAIL: tests/qalaAuditSink.test.js missing" >&2
  exit 1
fi

if [[ ! -f "tests/test_qala_audit_sink.py" ]]; then
  echo "[qala-audit-integrity-gate] FAIL: tests/test_qala_audit_sink.py missing" >&2
  exit 1
fi

echo "[qala-audit-integrity-gate] VERIFY: TypeScript/Node Qala audit chain"
node --test tests/qalaAuditSink.test.js

echo "[qala-audit-integrity-gate] VERIFY: Python Qala audit chain"
python3 -m unittest tests.test_qala_audit_sink

echo "[qala-audit-integrity-gate] PASS: Qala audit append-only hash-chain integrity verified"
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

info "Qal'a audit integrity gate (Q7)"
info "repo=$(pwd)"

VERIFIER=".agents/validators/qala_audit_sink.py"

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
