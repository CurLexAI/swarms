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
import os
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR  # noqa: E402

qala_audit_sink = _load_module(
    "_agents_pkg.validators.qala_audit_sink",
    AGENTS_DIR / "validators" / "qala_audit_sink.py",
)
QalaAuditSink = qala_audit_sink.QalaAuditSink
QALA_GENESIS_HASH = qala_audit_sink.QALA_GENESIS_HASH


@contextmanager
def _temporary_artifact_workspace() -> Iterator[Path]:
    """Run CLI tests from a private cwd containing artifacts/security."""
    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="qala-cli-") as tmp:
        workspace = Path(tmp)
        artifact_root = workspace / "artifacts" / "security"
        artifact_root.mkdir(parents=True)
        os.chdir(workspace)
        try:
            yield artifact_root
        finally:
            os.chdir(previous_cwd)


def _valid_append(
    sink: "Any",
    event: str = "input_validation_approved",
    payload: "dict[str, Any] | None" = None,
) -> "Any":
    return sink.append(
        event=event,
        trace_id="trace-id-1",
        span_id="span-id-1",
        tenant_id="tenant-A",
        payload=payload or {"k": "v"},
    )


class GenesisChainTests(unittest.TestCase):
    def test_first_record_chains_from_genesis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = _valid_append(sink)
            self.assertTrue(result.ok)
            self.assertEqual(result.value.prev_hash, QALA_GENESIS_HASH)
            self.assertNotEqual(result.value.record_hash, QALA_GENESIS_HASH)
            self.assertEqual(len(result.value.record_hash), 64)  # SHA-256 hex

    def test_subsequent_records_chain_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            a = _valid_append(sink, payload={"i": 1})
            b = _valid_append(sink, payload={"i": 2})
            c = _valid_append(sink, payload={"i": 3})
            self.assertEqual(b.value.prev_hash, a.value.record_hash)
            self.assertEqual(c.value.prev_hash, b.value.record_hash)

    def test_empty_file_verifies_as_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            verify = sink.verify_chain()
            self.assertTrue(verify.ok)
            self.assertEqual(verify.records_verified, 0)


class TamperEvidenceTests(unittest.TestCase):
    def test_modifying_a_prior_payload_breaks_chain(self) -> None:
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

    def test_modifying_prev_hash_breaks_chain(self) -> None:
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

    def test_inserting_a_record_breaks_chain(self) -> None:
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

    def test_truncating_a_record_breaks_chain(self) -> None:
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
    def test_rejects_unknown_event(self) -> None:
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

    def test_rejects_missing_trace_id(self) -> None:
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

    def test_rejects_missing_tenant(self) -> None:
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

    def test_payload_defaults_to_empty(self) -> None:
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

    def test_no_update_method(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit-noop.jsonl")
            self.assertFalse(hasattr(sink, "update"))
            self.assertFalse(hasattr(sink, "modify"))

    def test_no_delete_method(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit-noop.jsonl")
            self.assertFalse(hasattr(sink, "delete"))
            self.assertFalse(hasattr(sink, "remove"))


class DeterministicCanonicalizationTests(unittest.TestCase):
    def test_payload_key_order_does_not_affect_hash(self) -> None:
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


def _sample_events() -> "list[dict[str, Any]]":
    return [
        {
            "recordId": f"id-{i}",
            "event": "policy_decision",
            "traceId": f"trace-{i}",
            "spanId": "aegis_mcp.mcp_tool_discovery",
            "tenantId": "system",
            "occurredAt": f"2026-06-29T0{i}:00:00.000000Z",
            "payload": {"i": i},
        }
        for i in range(3)
    ]


class SealFromEventsTests(unittest.TestCase):
    """ADR-0008 §Decision.4: the chain is sealed from a merge-safe source."""

    def test_seal_is_deterministic_and_reproducible(self) -> None:
        events = _sample_events()
        with tempfile.TemporaryDirectory() as tmp:
            a = QalaAuditSink(Path(tmp) / "a.jsonl")
            b = QalaAuditSink(Path(tmp) / "b.jsonl")
            head_a = a.seal_from_events(events)
            head_b = b.seal_from_events(events)
            self.assertEqual(head_a, head_b)
            self.assertEqual(
                a.sink_path.read_bytes(), b.sink_path.read_bytes()
            )
            # Re-sealing the same source is idempotent (no append growth).
            head_a2 = a.seal_from_events(events)
            self.assertEqual(head_a, head_a2)

    def test_sealed_chain_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            sink.seal_from_events(_sample_events())
            self.assertTrue(sink.verify_chain().ok)

    def test_seal_rejects_unknown_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            bad = _sample_events()
            bad[1]["event"] = "garbage"
            with self.assertRaises(ValueError):
                sink.seal_from_events(bad)


class AnchorTruncationTests(unittest.TestCase):
    """Forward link-walking cannot catch tail truncation; the anchor can."""

    def test_anchor_match_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            head = sink.seal_from_events(_sample_events())
            res = sink.verify_chain(expected_count=3, expected_head_hash=head)
            self.assertTrue(res.ok)
            self.assertEqual(res.records_verified, 3)

    def test_tail_truncation_detected_by_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            head = sink.seal_from_events(_sample_events())
            # Drop the last record — the remaining prefix is still link-valid.
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            # Without the anchor the truncated prefix verifies (the gap).
            self.assertTrue(sink.verify_chain().ok)
            # With the anchor it fails closed.
            res = sink.verify_chain(expected_count=3, expected_head_hash=head)
            self.assertFalse(res.ok)
            self.assertEqual(res.error, "AUDIT_CHAIN_BROKEN")

    def test_head_hash_mismatch_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            sink.seal_from_events(_sample_events())
            res = sink.verify_chain(expected_count=3, expected_head_hash="0" * 64)
            self.assertFalse(res.ok)
            self.assertEqual(res.error, "AUDIT_CHAIN_BROKEN")

    def test_absent_ledger_with_nonzero_anchor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "missing.jsonl")
            res = sink.verify_chain(expected_count=5, expected_head_hash="x")
            self.assertFalse(res.ok)
            self.assertEqual(res.error, "AUDIT_CHAIN_BROKEN")

    def test_absent_ledger_with_zero_anchor_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "missing.jsonl")
            res = sink.verify_chain(
                expected_count=0, expected_head_hash=QALA_GENESIS_HASH
            )
            self.assertTrue(res.ok)


class SealVerifyCliTests(unittest.TestCase):
    """End-to-end CLI: seal --write-anchor, verify, then truncate -> rc 10."""

    def test_cli_rejects_external_paths_without_traceback(self) -> None:
        external_path = Path("/outside-confinement/audit.jsonl")
        rc = qala_audit_sink._main(["verify", "--path", str(external_path)])
        self.assertEqual(rc, 2)

    def test_cli_accepts_paths_under_artifact_boundary(self) -> None:
        with _temporary_artifact_workspace() as artifact_root:
            audit_path = artifact_root / "audit.jsonl"
            anchor_path = artifact_root / "anchor.json"
            rc = qala_audit_sink._main(
                ["verify", "--path", str(audit_path), "--anchor", str(anchor_path)]
            )
            self.assertEqual(rc, 0)

    def _write_events(self, artifact_root: Path) -> "tuple[Path, Path, Path]":
        events_path = artifact_root / "events.json"
        sink_path = artifact_root / "audit.jsonl"
        anchor_path = artifact_root / "anchor.json"
        events_path.write_text(
            json.dumps(_sample_events()), encoding="utf-8"
        )
        return events_path, sink_path, anchor_path

    def test_cli_seal_then_verify_then_truncate(self) -> None:
        with _temporary_artifact_workspace() as artifact_root:
            events_path, sink_path, anchor_path = self._write_events(artifact_root)
            seal_rc = qala_audit_sink._main(
                [
                    "seal",
                    "--events", str(events_path),
                    "--path", str(sink_path),
                    "--anchor", str(anchor_path),
                    "--write-anchor",
                ]
            )
            self.assertEqual(seal_rc, 0)
            self.assertTrue(anchor_path.exists())
            verify_rc = qala_audit_sink._main(
                ["verify", "--path", str(sink_path), "--anchor", str(anchor_path)]
            )
            self.assertEqual(verify_rc, 0)
            # Tail-truncate and re-verify: the anchor must force rc 10.
            lines = sink_path.read_text(encoding="utf-8").splitlines()
            sink_path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            broken_rc = qala_audit_sink._main(
                ["verify", "--path", str(sink_path), "--anchor", str(anchor_path)]
            )
            self.assertEqual(broken_rc, 10)


class CliPathConfinementTests(unittest.TestCase):
    """The CLI confines --anchor/--path/--events to the permitted roots
    (artifacts/security or the system temp directory), fail-closed."""

    def _events_file(self, tmp: str) -> Path:
        events_path = Path(tmp) / "events.json"
        events_path.write_text(json.dumps(_sample_events()), encoding="utf-8")
        return events_path

    def test_outside_root_anchor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            events_path = self._events_file(tmp)
            outside = Path(__file__).resolve().parent / "nope-anchor.json"
            rc = qala_audit_sink._main(
                [
                    "seal",
                    "--events", str(events_path),
                    "--path", str(Path(tmp) / "audit.jsonl"),
                    "--anchor", str(outside),
                ]
            )
            self.assertEqual(rc, 2)
            self.assertFalse(outside.exists())

    def test_outside_root_events_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(__file__).resolve().parent / "nope-events.json"
            rc = qala_audit_sink._main(
                [
                    "seal",
                    "--events", str(outside),
                    "--path", str(Path(tmp) / "audit.jsonl"),
                    "--anchor", str(Path(tmp) / "anchor.json"),
                ]
            )
            self.assertEqual(rc, 2)

    def test_outside_root_sink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(__file__).resolve().parent / "nope-audit.jsonl"
            rc = qala_audit_sink._main(
                [
                    "verify",
                    "--path", str(outside),
                    "--anchor", str(Path(tmp) / "anchor.json"),
                ]
            )
            self.assertEqual(rc, 2)

    def test_symlink_under_temp_escaping_the_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outside_dir = Path(__file__).resolve().parent
            link = Path(tmp) / "link"
            try:
                link.symlink_to(outside_dir, target_is_directory=True)
            except OSError:  # pragma: no cover — symlink-less filesystems
                self.skipTest("symlinks unavailable on this filesystem")
            events_path = self._events_file(tmp)
            rc = qala_audit_sink._main(
                [
                    "seal",
                    "--events", str(events_path),
                    "--path", str(Path(tmp) / "audit.jsonl"),
                    "--anchor", str(link / "escape.json"),
                    "--write-anchor",
                ]
            )
            self.assertEqual(rc, 2)
            self.assertFalse((outside_dir / "escape.json").exists())


class CliIoFailureTests(unittest.TestCase):
    """Constructor and anchor-write I/O failures return the documented
    rc=2 instead of leaking a traceback."""

    def test_verify_sink_below_file_component_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "blocker.txt"
            blocker.write_text("not a directory", encoding="utf-8")
            rc = qala_audit_sink._main(
                [
                    "verify",
                    "--path", str(blocker / "nested" / "audit.jsonl"),
                    "--anchor", str(Path(tmp) / "anchor.json"),
                ]
            )
            self.assertEqual(rc, 2)

    def test_seal_anchor_write_below_file_component_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            events_path = Path(tmp) / "events.json"
            events_path.write_text(
                json.dumps(_sample_events()), encoding="utf-8"
            )
            blocker = Path(tmp) / "blocker.txt"
            blocker.write_text("not a directory", encoding="utf-8")
            rc = qala_audit_sink._main(
                [
                    "seal",
                    "--events", str(events_path),
                    "--path", str(Path(tmp) / "audit.jsonl"),
                    "--anchor", str(blocker / "nested" / "anchor.json"),
                    "--write-anchor",
                ]
            )
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
