# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/router/*` deterministic routing policy.

Covers:
- `task_classifier.classify_task`: kind, risk, flags, whole-word matching
- `model_policy_engine.choose_route`: provider/model selection per profile
- `model_router.build_execution_plan`: step composition + reviewer gating
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import (  # noqa: E402
    model_policy_engine,
    model_router,
    router_types,
    task_classifier,
)

classify_task = task_classifier.classify_task
choose_route = model_policy_engine.choose_route
build_execution_plan = model_router.build_execution_plan
TaskKind = router_types.TaskKind
TaskProfile = router_types.TaskProfile


def _profile(**kwargs: Any) -> Any:
    base: dict[str, Any] = dict(
        kind=TaskKind.FAST_DRAFT,
        risk="low",
        requires_long_context=False,
        requires_arabic_legal_precision=False,
        requires_code_execution=False,
        requires_multimodal=False,
        estimated_context_tokens=256,
        requires_citations=False,
        tenant_id=None,
    )
    base.update(kwargs)
    return TaskProfile(**base)


class TaskClassifierKindTests(unittest.TestCase):
    def test_english_coding_task(self) -> None:
        profile = classify_task("Write a Python function to parse JSON")
        self.assertEqual(profile.kind, TaskKind.CODING)
        self.assertEqual(profile.risk, "high")
        self.assertTrue(profile.requires_code_execution)

    def test_code_review_task(self) -> None:
        profile = classify_task("Please review this Python code for bugs")
        self.assertEqual(profile.kind, TaskKind.CODE_REVIEW)
        self.assertEqual(profile.risk, "high")

    def test_agent_creation_task(self) -> None:
        profile = classify_task("Build an orchestrator agent for the swarm")
        self.assertEqual(profile.kind, TaskKind.AGENT_CREATION)

    def test_multimodal_task(self) -> None:
        profile = classify_task("Analyze this screenshot of the diagram")
        self.assertEqual(profile.kind, TaskKind.MULTIMODAL)
        self.assertTrue(profile.requires_multimodal)
        self.assertEqual(profile.risk, "medium")

    def test_legal_analysis_arabic(self) -> None:
        profile = classify_task("هل يخالف هذا النظام نظام حماية البيانات الشخصية؟")
        self.assertEqual(profile.kind, TaskKind.LEGAL_ANALYSIS)
        self.assertEqual(profile.risk, "critical")
        self.assertTrue(profile.requires_arabic_legal_precision)

    def test_legal_analysis_english_with_sama(self) -> None:
        profile = classify_task("Is this legal under SAMA regulation?")
        self.assertEqual(profile.kind, TaskKind.LEGAL_ANALYSIS)

    def test_critical_decision_default(self) -> None:
        profile = classify_task("Production payment auth fix")
        self.assertEqual(profile.risk, "critical")

    def test_long_context_analysis(self) -> None:
        long_task = " ".join(["analysis"] * 7000)
        profile = classify_task(long_task)
        self.assertEqual(profile.kind, TaskKind.LONG_CONTEXT_ANALYSIS)
        self.assertTrue(profile.requires_long_context)

    def test_default_fast_draft(self) -> None:
        profile = classify_task("Hello, what is the weather like today?")
        self.assertEqual(profile.kind, TaskKind.FAST_DRAFT)
        self.assertEqual(profile.risk, "low")

    def test_tenant_id_propagated(self) -> None:
        profile = classify_task("Hello", tenant_id="tenant-A")
        self.assertEqual(profile.tenant_id, "tenant-A")

    def test_estimated_context_tokens_scales_past_floor(self) -> None:
        # The classifier floors at 256 tokens; verify it scales above the floor
        # for sufficiently long inputs (max(256, words * 2)).
        short = classify_task("hi there")
        longer = classify_task(" ".join(["word"] * 500))
        self.assertEqual(short.estimated_context_tokens, 256)
        self.assertGreater(longer.estimated_context_tokens, 256)
        self.assertEqual(longer.estimated_context_tokens, 1000)


class TaskClassifierWordBoundaryTests(unittest.TestCase):
    """Whole-word matching: substrings must not trigger hint matches."""

    def test_decode_does_not_match_code_hint(self) -> None:
        profile = classify_task("How do I decode a base64 string?")
        self.assertNotEqual(profile.kind, TaskKind.CODING)

    def test_codename_does_not_match_code_hint(self) -> None:
        profile = classify_task("What is the codename of the project?")
        self.assertNotEqual(profile.kind, TaskKind.CODING)


class ChooseRouteTests(unittest.TestCase):
    def test_critical_risk_routes_to_anthropic(self) -> None:
        route = choose_route(
            _profile(kind=TaskKind.CRITICAL_DECISION, risk="critical")
        )
        self.assertEqual(route.provider, "anthropic")
        self.assertTrue(route.requires_reviewer)
        self.assertEqual(route.reviewer_agent_id, "bayyinah")

    def test_arabic_legal_routes_to_anthropic(self) -> None:
        route = choose_route(
            _profile(
                kind=TaskKind.LEGAL_ANALYSIS,
                risk="critical",
                requires_arabic_legal_precision=True,
            )
        )
        self.assertEqual(route.provider, "anthropic")
        self.assertTrue(route.requires_reviewer)

    def test_multimodal_high_risk_routes_to_openai_with_reviewer(self) -> None:
        route = choose_route(
            _profile(
                kind=TaskKind.MULTIMODAL, risk="medium", requires_multimodal=True
            )
        )
        self.assertEqual(route.provider, "openai")
        self.assertTrue(route.requires_reviewer)

    def test_multimodal_low_risk_routes_to_openai_no_reviewer(self) -> None:
        route = choose_route(
            _profile(
                kind=TaskKind.MULTIMODAL, risk="low", requires_multimodal=True
            )
        )
        self.assertEqual(route.provider, "openai")
        self.assertFalse(route.requires_reviewer)
        self.assertIsNone(route.reviewer_agent_id)

    def test_coding_routes_to_modal_mihwar(self) -> None:
        route = choose_route(_profile(kind=TaskKind.CODING, risk="high"))
        self.assertEqual(route.provider, "modal_vllm")
        self.assertEqual(route.model, "mihwar")
        self.assertTrue(route.requires_reviewer)

    def test_code_review_routes_to_modal_bayyinah_no_reviewer(self) -> None:
        route = choose_route(_profile(kind=TaskKind.CODE_REVIEW, risk="high"))
        self.assertEqual(route.provider, "modal_vllm")
        self.assertEqual(route.model, "bayyinah")
        self.assertFalse(route.requires_reviewer)

    def test_agent_creation_routes_to_modal(self) -> None:
        route = choose_route(_profile(kind=TaskKind.AGENT_CREATION, risk="high"))
        self.assertEqual(route.provider, "modal_vllm")
        self.assertEqual(route.model, "mihwar")
        self.assertTrue(route.requires_reviewer)

    def test_fast_draft_low_risk_no_reviewer(self) -> None:
        route = choose_route(_profile(kind=TaskKind.FAST_DRAFT, risk="low"))
        self.assertEqual(route.provider, "openai")
        self.assertFalse(route.requires_reviewer)

    def test_long_context_routes_to_anthropic(self) -> None:
        route = choose_route(
            _profile(
                kind=TaskKind.LONG_CONTEXT_ANALYSIS,
                risk="medium",
                requires_long_context=True,
            )
        )
        self.assertEqual(route.provider, "anthropic")
        self.assertTrue(route.requires_reviewer)


class BuildExecutionPlanTests(unittest.TestCase):
    def test_minimum_steps(self) -> None:
        plan = build_execution_plan("Hello")
        self.assertIn("classify_task", plan.steps)
        self.assertIn("choose_policy_route", plan.steps)

    def test_legal_analysis_includes_legal_claim_discipline(self) -> None:
        plan = build_execution_plan(
            "هل يخالف هذا النظام نظام حماية البيانات الشخصية ساما؟"
        )
        self.assertIn("legal_claim_discipline", plan.steps)
        self.assertIn("require_citations", plan.steps)

    def test_agent_creation_includes_secure_design_review(self) -> None:
        plan = build_execution_plan("Build a swarm orchestrator agent")
        self.assertIn("secure_agent_design_review", plan.steps)

    def test_validation_required_for_high_risk(self) -> None:
        plan = build_execution_plan("Refactor this Python code for performance")
        self.assertTrue(plan.validation_required)
        self.assertIn("bayyinah_validation_gate", plan.steps)

    def test_code_execution_evidence_step_present(self) -> None:
        plan = build_execution_plan("Write a Python build script")
        self.assertIn("require_validation_evidence", plan.steps)

    def test_steps_is_tuple(self) -> None:
        plan = build_execution_plan("Hello")
        self.assertIsInstance(plan.steps, tuple)


if __name__ == "__main__":
    unittest.main()
