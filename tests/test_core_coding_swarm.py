# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Offline unit tests for `.agents/core_coding_swarm.py`.

All tests run without network access. No live Mihwar or Bayyinah endpoints
are called. The CORE_SWARM_ENABLE_LIVE_CALLS flag is explicitly set to
"false" (the default) for every test.

Test classes:
    SwarmOfflinePipelineTests  — happy-path offline execution.
    SwarmSovereigntyGateTests  — ALLOW_EXTERNAL_AI fail-closed behaviour.
    SwarmComplianceGateTests   — compliance_check=False rejection.
    SwarmEscalationGateTests   — is_valid=False escalation.
    SwarmModelTests            — Pydantic model construction and fields.
    SwarmAuditTrailTests       — audit_trail_id format and log truncation.
"""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

# ── Import core_coding_swarm from .agents/ ──────────────────────────────────
# The .agents directory starts with a dot, so we cannot import it as a
# normal package. We load it via importlib into a synthetic package that
# does not conflict with any existing sys.modules entries.

REPO_ROOT = Path(__file__).resolve().parent.parent
_SWARM_FILE = REPO_ROOT / ".agents" / "core_coding_swarm.py"

_PKG_NAME = "_swarm_test_pkg"


def _load_swarm_module() -> types.ModuleType:
    if _PKG_NAME in sys.modules:
        return sys.modules[_PKG_NAME]
    spec = importlib.util.spec_from_file_location(_PKG_NAME, _SWARM_FILE)
    assert spec is not None and spec.loader is not None, f"Cannot load {_SWARM_FILE}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_PKG_NAME] = mod
    spec.loader.exec_module(mod)
    return mod


_swarm = _load_swarm_module()
CoreCodingSwarm: Any = _swarm.CoreCodingSwarm
MihwarPlan: Any = _swarm.MihwarPlan
BayyinahValidation: Any = _swarm.BayyinahValidation
SwarmResult: Any = _swarm.SwarmResult
_truncate_for_log: Any = _swarm._truncate_for_log
_make_audit_trail_id: Any = _swarm._make_audit_trail_id


# ── Helpers ──────────────────────────────────────────────────────────────────

def _offline_env() -> dict[str, str]:
    """Environment overrides that guarantee offline, sovereignty-safe execution."""
    return {
        "ALLOW_EXTERNAL_AI": "false",
        "CORE_SWARM_ENABLE_LIVE_CALLS": "false",
    }


# ── Test classes ─────────────────────────────────────────────────────────────


class SwarmOfflinePipelineTests(unittest.TestCase):
    """Happy-path offline execution returns SUCCESS."""

    def test_execute_task_returns_swarm_result(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Add rate limiting to the API gateway")
        self.assertIsInstance(result, SwarmResult)

    def test_execute_task_status_success(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Refactor the auth module")
        self.assertEqual(result.status, "SUCCESS")

    def test_execute_task_final_output_not_empty(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Implement HMAC middleware")
        self.assertTrue(len(result.final_output) > 0)

    def test_execute_task_audit_trail_id_format(self) -> None:
        """audit_trail_id must match SWARM-<date>-<hex8> pattern."""
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Write a unit test for the router")
        self.assertRegex(result.audit_trail_id, r"^SWARM-\d{8}-\d{6}-[0-9a-f]{8}$")

    def test_phase_1_returns_mihwar_plan(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            plan = swarm.phase_1_mihwar_planning("Test task", "TASK-001")
        self.assertIsInstance(plan, MihwarPlan)
        self.assertEqual(plan.task_id, "TASK-001")
        self.assertTrue(plan.compliance_check)

    def test_phase_2_returns_bayyinah_validation(self) -> None:
        plan = MihwarPlan(
            task_id="TASK-002",
            architecture_decision="test decision",
            compliance_check=True,
            required_evidence=["doc_a", "doc_b"],
        )
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            validation = swarm.phase_2_bayyinah_validation(plan)
        self.assertIsInstance(validation, BayyinahValidation)
        self.assertTrue(validation.is_valid)
        self.assertEqual(validation.plan_id, "TASK-002")

    def test_phase_2_evidence_matches_plan(self) -> None:
        expected = ["policy_doc_v1", "compliance_framework_2024"]
        plan = MihwarPlan(
            task_id="TASK-003",
            architecture_decision="test",
            compliance_check=True,
            required_evidence=expected,
        )
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            validation = swarm.phase_2_bayyinah_validation(plan)
        self.assertEqual(sorted(validation.evidence_retrieved), sorted(expected))


class SwarmSovereigntyGateTests(unittest.TestCase):
    """ALLOW_EXTERNAL_AI=true must be rejected immediately (fail-closed)."""

    def test_external_ai_enabled_returns_rejected(self) -> None:
        env = {"ALLOW_EXTERNAL_AI": "true", "CORE_SWARM_ENABLE_LIVE_CALLS": "false"}
        with patch.dict("os.environ", env):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Any task")
        self.assertEqual(result.status, "REJECTED")

    def test_external_ai_enabled_audit_id_is_violation_marker(self) -> None:
        env = {"ALLOW_EXTERNAL_AI": "true", "CORE_SWARM_ENABLE_LIVE_CALLS": "false"}
        with patch.dict("os.environ", env):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Any task")
        self.assertEqual(result.audit_trail_id, "SOVEREIGNTY-VIOLATION")

    def test_external_ai_disabled_does_not_reject(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            result = swarm.execute_task("Safe task")
        self.assertNotEqual(result.status, "REJECTED")


class SwarmComplianceGateTests(unittest.TestCase):
    """compliance_check=False on the plan must return REJECTED."""

    def test_non_compliant_plan_returns_rejected(self) -> None:
        """Patch phase_1 to return a non-compliant plan."""
        non_compliant = MihwarPlan(
            task_id="TASK-NC",
            architecture_decision="violates policy",
            compliance_check=False,
            required_evidence=[],
        )
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            with patch.object(swarm, "phase_1_mihwar_planning", return_value=non_compliant):
                result = swarm.execute_task("Bad task")
        self.assertEqual(result.status, "REJECTED")


class SwarmEscalationGateTests(unittest.TestCase):
    """is_valid=False on validation must return ESCALATED."""

    def test_invalid_validation_returns_escalated(self) -> None:
        conflict_validation = BayyinahValidation(
            plan_id="TASK-CONF",
            evidence_retrieved=["doc_a"],
            is_valid=False,
            conflicts_detected="Policy conflict detected in evidence.",
        )
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            with patch.object(
                swarm, "phase_2_bayyinah_validation", return_value=conflict_validation
            ):
                result = swarm.execute_task("Conflicting task")
        self.assertEqual(result.status, "ESCALATED")


class SwarmErrorHandlingTests(unittest.TestCase):
    """RuntimeError from live calls must surface as ERROR status."""

    def test_runtime_error_in_phase1_returns_error(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            with patch.object(
                swarm,
                "phase_1_mihwar_planning",
                side_effect=RuntimeError("Endpoint unreachable"),
            ):
                result = swarm.execute_task("Any task")
        self.assertEqual(result.status, "ERROR")

    def test_runtime_error_in_phase2_returns_error(self) -> None:
        with patch.dict("os.environ", _offline_env()):
            swarm = CoreCodingSwarm()
            with patch.object(
                swarm,
                "phase_2_bayyinah_validation",
                side_effect=RuntimeError("Bayyinah unavailable"),
            ):
                result = swarm.execute_task("Any task")
        self.assertEqual(result.status, "ERROR")


class SwarmModelTests(unittest.TestCase):
    """Pydantic model construction and field validation."""

    def test_mihwar_plan_fields(self) -> None:
        plan = MihwarPlan(
            task_id="T1",
            architecture_decision="Use HMAC middleware",
            compliance_check=True,
            required_evidence=["doc1"],
        )
        self.assertEqual(plan.task_id, "T1")
        self.assertTrue(plan.compliance_check)
        self.assertEqual(plan.required_evidence, ["doc1"])

    def test_bayyinah_validation_optional_conflict(self) -> None:
        v = BayyinahValidation(
            plan_id="P1",
            evidence_retrieved=[],
            is_valid=True,
        )
        self.assertIsNone(v.conflicts_detected)

    def test_swarm_result_status_values(self) -> None:
        for status in ("SUCCESS", "REJECTED", "ESCALATED", "ERROR"):
            r = SwarmResult(
                status=status,
                final_output="out",
                audit_trail_id="SWARM-20260101-000000-abcd1234",
            )
            self.assertEqual(r.status, status)


class SwarmAuditTrailTests(unittest.TestCase):
    """audit_trail_id helpers and log truncation."""

    def test_truncate_short_string_unchanged(self) -> None:
        short = "short text"
        self.assertEqual(_truncate_for_log(short), short)

    def test_truncate_long_string_appends_marker(self) -> None:
        long = "x" * 200
        result = _truncate_for_log(long)
        self.assertIn("[truncated]", result)
        self.assertLessEqual(len(result), 80 + len("...[truncated]"))

    def test_make_audit_trail_id_format(self) -> None:
        trail_id = _make_audit_trail_id("some task description")
        self.assertRegex(trail_id, r"^SWARM-\d{8}-\d{6}-[0-9a-f]{8}$")

    def test_make_audit_trail_id_deterministic_on_same_input(self) -> None:
        a = _make_audit_trail_id("same description")
        b = _make_audit_trail_id("same description")
        # Timestamps may differ by a second in slow CI; only the hash suffix
        # is guaranteed to be identical for the same input.
        self.assertEqual(a[-8:], b[-8:])

    def test_make_audit_trail_id_different_for_different_inputs(self) -> None:
        a = _make_audit_trail_id("task A")
        b = _make_audit_trail_id("task B")
        self.assertNotEqual(a[-8:], b[-8:])


if __name__ == "__main__":
    unittest.main()
