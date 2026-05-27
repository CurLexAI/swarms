# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/validators/qala_audit_sink.py`.

Contracts under test (per ADR-0003 §Q7):

1. Genesis record is chained from "GENESIS".
2. Each subsequent record's prev_hash equals the prior record_hash.
3. Tampering with any prior record's bytes invalidates the chain
   verification.
4. append() rejects unknown events and missing trace fields with
   typed error codes (AUDIT_INVALID_EVENT, AUDIT_INVALID_INPUT).
5. Canonicalization is deterministic — re-hashing on read matches
   the hash computed on write.
6. The sink is append-only — no update/delete API surface exists.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR  # noqa: E402

qala_audit_sink = _load_module(
    "_agents_pkg.validators.qala_audit_sink",
    AGENTS_DIR / "validators" / "qala_audit_sink.py",
)
QalaAuditSink = qala_audit_sink.QalaAuditSink
QALA_GENESIS_HASH = qala_audit_sink.QALA_GENESIS_HASH


def _valid_append(sink, event="input_validation_approved", payload=None):
    return sink.append(
        event=event,
        trace_id="trace-id-1",
        span_id="span-id-1",
        tenant_id="tenant-A",
        payload=payload or {"k": "v"},
    )


class GenesisChainTests(unittest.TestCase):
    def test_first_record_chains_from_genesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = _valid_append(sink)
            self.assertTrue(result.ok)
            self.assertEqual(result.value.prev_hash, QALA_GENESIS_HASH)
            self.assertNotEqual(result.value.record_hash, QALA_GENESIS_HASH)
            self.assertEqual(len(result.value.record_hash), 64)  # SHA-256 hex

    def test_subsequent_records_chain_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            a = _valid_append(sink, payload={"i": 1})
            b = _valid_append(sink, payload={"i": 2})
            c = _valid_append(sink, payload={"i": 3})
            self.assertEqual(b.value.prev_hash, a.value.record_hash)
            self.assertEqual(c.value.prev_hash, b.value.record_hash)

    def test_empty_file_verifies_as_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            verify = sink.verify_chain()
            self.assertTrue(verify.ok)
            self.assertEqual(verify.records_verified, 0)


class TamperEvidenceTests(unittest.TestCase):
    def test_modifying_a_prior_payload_breaks_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _valid_append(sink, payload={"i": 1})
            _valid_append(sink, payload={"i": 2})
            _valid_append(sink, payload={"i": 3})

            # Verify chain is intact first.
            self.assertTrue(sink.verify_chain().ok)

            # Tamper with the first record's payload.
            lines = path.read_text(encoding="utf-8").splitlines()
            first = json.loads(lines[0])
            first["payload"]["i"] = 99
            lines[0] = json.dumps(first)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            verify = sink.verify_chain()
            self.assertFalse(verify.ok)
            self.assertEqual(verify.error, "AUDIT_CHAIN_BROKEN")
            self.assertEqual(verify.at_record, 0)

    def test_modifying_prev_hash_breaks_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _valid_append(sink)
            _valid_append(sink)

            lines = path.read_text(encoding="utf-8").splitlines()
            second = json.loads(lines[1])
            second["prevHash"] = "0" * 64
            lines[1] = json.dumps(second)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            verify = sink.verify_chain()
            self.assertFalse(verify.ok)
            self.assertEqual(verify.at_record, 1)

    def test_inserting_a_record_breaks_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _valid_append(sink, payload={"i": 1})
            _valid_append(sink, payload={"i": 2})

            lines = path.read_text(encoding="utf-8").splitlines()
            # Inject a fabricated record between record 0 and record 1.
            fake = json.loads(lines[0])
            fake["payload"] = {"i": 99}
            fake["recordId"] = "fabricated"
            lines = [lines[0], json.dumps(fake), lines[1]]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            verify = sink.verify_chain()
            self.assertFalse(verify.ok)

    def test_truncating_a_record_breaks_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _valid_append(sink)
            _valid_append(sink)
            # Replace second record with an invalid-JSON fragment.
            lines = path.read_text(encoding="utf-8").splitlines()
            lines[1] = lines[1][: len(lines[1]) // 2]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            verify = sink.verify_chain()
            self.assertFalse(verify.ok)


class InputValidationTests(unittest.TestCase):
    def test_rejects_unknown_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = sink.append(
                event="garbage",
                trace_id="t",
                span_id="s",
                tenant_id="x",
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "AUDIT_INVALID_EVENT")

    def test_rejects_missing_trace_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = sink.append(
                event="input_validation_approved",
                trace_id="",
                span_id="s",
                tenant_id="x",
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "AUDIT_INVALID_INPUT")

    def test_rejects_missing_tenant(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = sink.append(
                event="input_validation_approved",
                trace_id="t",
                span_id="s",
                tenant_id="",
            )
            self.assertFalse(result.ok)
            self.assertEqual(result.error, "AUDIT_INVALID_INPUT")

    def test_payload_defaults_to_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = sink.append(
                event="input_validation_approved",
                trace_id="t",
                span_id="s",
                tenant_id="x",
            )
            self.assertTrue(result.ok)
            self.assertEqual(result.value.payload, {})


class AppendOnlyApiTests(unittest.TestCase):
    """The sink must NOT expose an update or delete method."""

    def test_no_update_method(self):
        sink = QalaAuditSink(Path(tempfile.gettempdir()) / "audit-noop.jsonl")
        self.assertFalse(hasattr(sink, "update"))
        self.assertFalse(hasattr(sink, "modify"))

    def test_no_delete_method(self):
        sink = QalaAuditSink(Path(tempfile.gettempdir()) / "audit-noop.jsonl")
        self.assertFalse(hasattr(sink, "delete"))
        self.assertFalse(hasattr(sink, "remove"))


class DeterministicCanonicalizationTests(unittest.TestCase):
    def test_payload_key_order_does_not_affect_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink_a = QalaAuditSink(Path(tmp) / "a.jsonl")
            sink_b = QalaAuditSink(Path(tmp) / "b.jsonl")
            a = sink_a.append(
                event="input_validation_approved",
                trace_id="t",
                span_id="s",
                tenant_id="x",
                payload={"a": 1, "b": 2},
                occurred_at="2026-05-15T00:00:00Z",
            )
            b = sink_b.append(
                event="input_validation_approved",
                trace_id="t",
                span_id="s",
                tenant_id="x",
                payload={"b": 2, "a": 1},
                occurred_at="2026-05-15T00:00:00Z",
            )
            self.assertEqual(a.value.record_hash, b.value.record_hash)


if __name__ == "__main__":
    unittest.main()
