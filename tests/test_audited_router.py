# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Tests for the audited router wrapper (.agents/router/audited_router.py).

Contracts under test:

1. A successful route emits classification_decision + route_decision into
   the sealed sink, returns the same ExecutionPlan the pure router would,
   and leaves the hash chain intact.
2. The raw task text is NEVER written to the sink (PII discipline).
3. When choose_route has no route (ValueError), route_blocked is recorded
   and the error propagates — no plan is returned.
4. Fail-closed: if an audit append fails, AuditError is raised.
5. The pure router (build_execution_plan) is not mutated by the wrapper.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR, model_router  # noqa: E402

qala_audit_sink = _load_module(
    "_agents_pkg.validators.qala_audit_sink",
    AGENTS_DIR / "validators" / "qala_audit_sink.py",
)
audited_router = _load_module(
    "_agents_pkg.router.audited_router",
    AGENTS_DIR / "router" / "audited_router.py",
)

QalaAuditSink = qala_audit_sink.QalaAuditSink
build_audited_execution_plan = audited_router.build_audited_execution_plan
AuditError = audited_router.AuditError

# A coding task routes cleanly (kind=CODING -> modal_vllm). The marker lets
# us assert the raw task text never reaches the sink.
_MARKER = "SECRET_MARKER_z9q"
_CODING_TASK = f"refactor the python function {_MARKER} and add a unit test"


def _events(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


class AuditedRouterTests(unittest.TestCase):
    def test_route_decision_recorded_and_chain_intact(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            plan = build_audited_execution_plan(
                _CODING_TASK, tenant_id="tenant-A", subject_id="q-001", sink=sink
            )

            # Same plan the pure router would produce.
            expected = model_router.build_execution_plan(
                _CODING_TASK, tenant_id="tenant-A"
            )
            self.assertEqual(plan, expected)

            events = _events(path)
            kinds = [e["event"] for e in events]
            self.assertEqual(kinds, ["classification_decision", "route_decision"])
            self.assertTrue(sink.verify_chain().ok)

            route_evt = events[1]
            self.assertEqual(route_evt["payload"]["subject_id"], "q-001")
            self.assertEqual(route_evt["payload"]["provider"], expected.route.provider)
            self.assertEqual(route_evt["payload"]["model"], expected.route.model)

    def test_raw_task_text_never_written(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)
            build_audited_execution_plan(_CODING_TASK, tenant_id="tenant-A", sink=sink)
            self.assertNotIn(_MARKER, path.read_text(encoding="utf-8"))

    def test_route_blocked_recorded_then_raises(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "audit.jsonl"
            sink = QalaAuditSink(path)

            def _raise(*_args, **_kwargs):
                raise ValueError("No route defined for task kind")

            original = audited_router.build_execution_plan
            audited_router.build_execution_plan = _raise
            try:
                with self.assertRaises(ValueError):
                    build_audited_execution_plan(
                        _CODING_TASK, tenant_id="tenant-A", sink=sink
                    )
            finally:
                audited_router.build_execution_plan = original

            kinds = [e["event"] for e in _events(path)]
            self.assertEqual(kinds, ["classification_decision", "route_blocked"])
            self.assertTrue(sink.verify_chain().ok)

    def test_fail_closed_when_append_fails(self) -> None:
        class _FailingSink:
            def append(self, **_kwargs):
                class _Err:
                    ok = False
                    error = "AUDIT_WRITE_FAILED"
                    message = "disk full"

                return _Err()

        with self.assertRaises(AuditError):
            build_audited_execution_plan(
                _CODING_TASK, tenant_id="tenant-A", sink=_FailingSink()
            )

    def test_pure_router_not_mutated(self) -> None:
        # The wrapper must not have side-effected the pure router module.
        with TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            build_audited_execution_plan(_CODING_TASK, tenant_id="t", sink=sink)
        # Pure call still deterministic and side-effect free.
        a = model_router.build_execution_plan(_CODING_TASK, tenant_id="t")
        b = model_router.build_execution_plan(_CODING_TASK, tenant_id="t")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
