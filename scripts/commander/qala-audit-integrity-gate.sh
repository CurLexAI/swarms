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
