# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for scripts/commander/qala-audit-integrity-gate.sh.

Under the ADR-0008 §Decision.4 generated-artifact model the gate is
two-phase: it deterministically *seals* the chain from the merge-safe event
source (``qala-audit.events.json``) and then *verifies* it against the
committed anchor (``qala-audit.anchor.json``: recordCount + headHash). These
tests lock the gate's BEHAVIOR — exit code and result line — for the cases
that matter:

1. A sealed chain whose anchor matches PASSes.
2. An event source that diverges from its anchor (e.g. tail truncation)
   FAILs (fail-closed) with AUDIT_CHAIN_BROKEN.
3. With no event source, a tampered runtime chain still FAILs.
4. With no event source, no anchor, and no log, the gate PASSes
   (lazy sink, pre-activation state).

Each test points QALA_AUDIT_EVENTS_PATH / QALA_AUDIT_ANCHOR_PATH /
QALA_AUDIT_SINK_PATH at a private temp dir so the gate's inputs are fully
controlled and independent of the repo's committed ledger.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR  # noqa: E402

qala_audit_sink = _load_module(
    "_agents_pkg.validators.qala_audit_sink",
    AGENTS_DIR / "validators" / "qala_audit_sink.py",
)
QalaAuditSink = qala_audit_sink.QalaAuditSink

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "commander" / "qala-audit-integrity-gate.sh"
VERIFIER = REPO_ROOT / ".agents" / "validators" / "qala_audit_sink.py"


def _run_gate(env_overrides: dict[str, str]) -> "subprocess.CompletedProcess[str]":
    env = {"PATH": os.environ.get("PATH", "")}
    env.update(env_overrides)
    return subprocess.run(
        ["bash", str(GATE), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def _seal_cli(
    events_path: Path, sink_path: Path, anchor_path: Path, *, write_anchor: bool
) -> "subprocess.CompletedProcess[str]":
    cmd = [
        sys.executable,
        str(VERIFIER),
        "seal",
        "--events",
        str(events_path),
        "--path",
        str(sink_path),
        "--anchor",
        str(anchor_path),
    ]
    if write_anchor:
        cmd.append("--write-anchor")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def _events(count: int) -> list[dict[str, Any]]:
    return [
        {
            "recordId": f"{i:08d}-0000-0000-0000-000000000000",
            "event": "policy_decision",
            "traceId": f"trace-{i}",
            "spanId": f"span-{i}",
            "tenantId": "tenant-A",
            "occurredAt": f"2026-06-01T00:00:{i:02d}.000000Z",
            "payload": {"i": i},
        }
        for i in range(count)
    ]


def _write_events(path: Path, count: int) -> None:
    path.write_text(json.dumps(_events(count), indent=2) + "\n", encoding="utf-8")


def _append_valid(sink: Any, payload: dict[str, Any]) -> Any:
    return sink.append(
        event="policy_decision",
        trace_id="trace-1",
        span_id="span-1",
        tenant_id="tenant-A",
        payload=payload,
    )


class AuditIntegrityGateTests(unittest.TestCase):
    def test_sealed_chain_matching_anchor_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.json"
            sink = Path(tmp) / "audit.jsonl"
            anchor = Path(tmp) / "anchor.json"
            _write_events(events, 3)
            seal = _seal_cli(events, sink, anchor, write_anchor=True)
            self.assertEqual(seal.returncode, 0, msg=seal.stdout + seal.stderr)

            result = _run_gate(
                {
                    "QALA_AUDIT_EVENTS_PATH": str(events),
                    "QALA_AUDIT_SINK_PATH": str(sink),
                    "QALA_AUDIT_ANCHOR_PATH": str(anchor),
                }
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"expected PASS, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] PASS", result.stdout)
            self.assertIn("AUDIT_CHAIN_OK records_verified=3", result.stdout)

    def test_event_source_diverging_from_anchor_fails(self) -> None:
        # Seal + anchor over 3 events, then truncate the source to 2 without
        # updating the anchor. The re-seal produces a still-link-valid 2-record
        # chain (the old forward-only walk would PASS), but the anchor pins
        # count=3, so the gate must FAIL — closing the tail-truncation gap.
        with TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.json"
            sink = Path(tmp) / "audit.jsonl"
            anchor = Path(tmp) / "anchor.json"
            _write_events(events, 3)
            seal = _seal_cli(events, sink, anchor, write_anchor=True)
            self.assertEqual(seal.returncode, 0, msg=seal.stdout + seal.stderr)

            _write_events(events, 2)  # drop the last event; anchor still says 3

            result = _run_gate(
                {
                    "QALA_AUDIT_EVENTS_PATH": str(events),
                    "QALA_AUDIT_SINK_PATH": str(sink),
                    "QALA_AUDIT_ANCHOR_PATH": str(anchor),
                }
            )
            self.assertEqual(
                result.returncode,
                1,
                msg=f"expected FAIL, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] FAIL", result.stdout)
            self.assertIn("AUDIT_CHAIN_BROKEN", result.stdout)

    def test_tampered_runtime_chain_without_event_source_fails(self) -> None:
        # No event source (a live runtime ledger). The gate skips sealing and
        # verifies the chain as-is; a tampered record must FAIL.
        with TemporaryDirectory() as tmp:
            sink = Path(tmp) / "audit.jsonl"
            s = QalaAuditSink(sink)
            _append_valid(s, {"i": 1})
            _append_valid(s, {"i": 2})
            lines = sink.read_text(encoding="utf-8").splitlines()
            first = json.loads(lines[0])
            first["payload"]["i"] = 99
            lines[0] = json.dumps(first)
            sink.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = _run_gate(
                {
                    "QALA_AUDIT_EVENTS_PATH": str(Path(tmp) / "no-events.json"),
                    "QALA_AUDIT_SINK_PATH": str(sink),
                    "QALA_AUDIT_ANCHOR_PATH": str(Path(tmp) / "no-anchor.json"),
                }
            )
            self.assertEqual(
                result.returncode,
                1,
                msg=f"expected FAIL, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] FAIL", result.stdout)
            self.assertIn("AUDIT_CHAIN_BROKEN", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_absent_log_no_anchor_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            result = _run_gate(
                {
                    "QALA_AUDIT_EVENTS_PATH": str(Path(tmp) / "no-events.json"),
                    "QALA_AUDIT_SINK_PATH": str(Path(tmp) / "does-not-exist.jsonl"),
                    "QALA_AUDIT_ANCHOR_PATH": str(Path(tmp) / "no-anchor.json"),
                }
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=f"expected PASS for absent log, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] PASS", result.stdout)
            self.assertIn("AUDIT_CHAIN_OK records_verified=0", result.stdout)


if __name__ == "__main__":
    unittest.main()
