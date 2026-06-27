# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Qarar model router entrypoint."""

from __future__ import annotations

from .model_policy_engine import choose_route
from .task_classifier import classify_task
from .types import ExecutionPlan, TaskKind


def build_execution_plan(task: str, tenant_id: str | None = None) -> ExecutionPlan:
    profile = classify_task(task, tenant_id=tenant_id)
    route = choose_route(profile)

    steps: list[str] = [
        "classify_task",
        "choose_policy_route",
    ]

    if profile.requires_citations:
        steps.append("require_citations")
    if profile.requires_code_execution:
        steps.append("require_validation_evidence")

    validation_required = route.requires_reviewer or (
        profile.risk in {"high", "critical"} and route.reviewer_agent_id is not None
    )
    if validation_required:
        steps.append("bayyinah_validation_gate")

    if profile.kind == TaskKind.AGENT_CREATION:
        steps.append("secure_agent_design_review")
    if profile.kind == TaskKind.LEGAL_ANALYSIS:
        steps.append("legal_claim_discipline")

    primary_agent_id = route.model if route.provider in ("modal_vllm", "local_ollama") else "qarar-router"

    return ExecutionPlan(
        primary_agent_id=primary_agent_id,
        route=route,
        validation_required=validation_required,
        steps=tuple(steps),
    )
