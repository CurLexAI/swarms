# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for scripts/commander/qala-audit-integrity-gate.sh.

The gate wraps the existing QalaAuditSink.verify_chain engine and turns
chain integrity into a runnable CI gate (ADR-0003 §Q7). These tests lock
the gate's BEHAVIOR — exit code and result line — for the three cases
that matter:

1. An intact chain PASSes.
2. A tampered chain FAILs (fail-closed) with AUDIT_CHAIN_BROKEN.
3. An absent/empty log PASSes (lazy sink, pre-activation state).
"""

from __future__ import annotations

import json
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


def _run_gate(sink_path: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["bash", str(GATE), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        env={"QALA_AUDIT_SINK_PATH": str(sink_path), "PATH": _path_env()},
        timeout=30,
    )


def _path_env() -> str:
    import os

    return os.environ.get("PATH", "")


def _append_valid(sink: Any, payload: dict[str, Any]) -> Any:
    return sink.append(
        event="policy_decision",
        trace_id="trace-1",
        span_id="span-1",
        tenant_id="tenant-A",
        payload=payload,
    )


class AuditIntegrityGateTests(unittest.TestCase):
    def test_intact_chain_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _append_valid(sink, {"i": 1})
            _append_valid(sink, {"i": 2})
            _append_valid(sink, {"i": 3})

            result = _run_gate(path)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"expected PASS, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] PASS", result.stdout)
            self.assertIn("AUDIT_CHAIN_OK records_verified=3", result.stdout)

    def test_tampered_chain_fails(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _append_valid(sink, {"i": 1})
            _append_valid(sink, {"i": 2})

            # Tamper with the first record's payload after the fact.
            lines = path.read_text(encoding="utf-8").splitlines()
            first = json.loads(lines[0])
            first["payload"]["i"] = 99
            lines[0] = json.dumps(first)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            result = _run_gate(path)
            self.assertEqual(
                result.returncode,
                1,
                msg=f"expected FAIL, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] FAIL", result.stdout)
            self.assertIn("AUDIT_CHAIN_BROKEN", result.stdout)

    def test_malformed_record_reports_chain_broken(self) -> None:
        # A record that is valid JSON but missing required fields must be
        # classified as AUDIT_CHAIN_BROKEN (gate rc=1), never a traceback,
        # so the CLI keeps its documented exit-code contract.
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            _append_valid(sink, {"i": 1})
            first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            malformed = {"prevHash": first["recordHash"], "recordHash": "deadbeef"}
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(malformed) + "\n")

            result = _run_gate(path)
            self.assertEqual(
                result.returncode,
                1,
                msg=f"expected FAIL, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("AUDIT_CHAIN_BROKEN", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_absent_log_passes(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "does-not-exist.jsonl"
            result = _run_gate(path)
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
