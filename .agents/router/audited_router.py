# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Audited wrapper around the deterministic Qarar router.

`build_execution_plan` is pure, deterministic policy code and must stay
free of side effects (see `.agents/router/types.py`). This wrapper adds the
*mandatory* audit side effect at the call boundary: every routing decision
is recorded into the sealed, hash-chained Qal'a audit sink (Q7) before the
plan is returned. The router itself is untouched and unaware of auditing.

Events emitted (all defined in `qala_audit_sink`):
  - classification_decision : the TaskProfile the classifier produced.
  - route_decision          : the ModelRoute the policy engine chose.
  - route_blocked           : `choose_route` had no route for the
                              (kind, risk) combination and raised — no plan
                              is returned.

PII discipline (ADR-0003 §Q7): the raw task text is NEVER written to the
sink. Only derived, non-sensitive metadata (kind, risk, provider, model,
reviewer) is recorded.

Fail-closed: if an audit append fails, ``AuditError`` is raised and no
un-audited execution plan is returned to the caller. A routing decision
that cannot be durably audited is not a usable decision.
"""

from __future__ import annotations

from typing import Any

from ..validators.qala_audit_sink import QalaAuditSink
from ..validators.qala_trace import QalaTraceContext, new_trace
from .model_router import build_execution_plan
from .task_classifier import classify_task
from .types import ExecutionPlan, TaskProfile

# Routing is a deterministic policy decision; the Q6 phase that fits is
# "policy_check".
_ROUTING_PHASE = "policy_check"
_DEFAULT_TENANT = "system"


class AuditError(RuntimeError):
    """Raised when a routing decision could not be durably audited.

    Fail-closed: the caller must not treat an execution plan as valid if
    its decision was not recorded in the sealed audit chain.
    """


def _require_ok(result: Any) -> None:
    if not getattr(result, "ok", False):
        error = getattr(result, "error", "AUDIT_WRITE_FAILED")
        message = getattr(result, "message", "audit append failed")
        raise AuditError(f"{error}: {message}")


def _profile_payload(profile: TaskProfile, subject_id: str) -> dict[str, Any]:
    # Derived metadata only — never the raw task text (PII discipline).
    return {
        "subject_id": subject_id,
        "kind": profile.kind.value,
        "risk": profile.risk,
        "requires_long_context": profile.requires_long_context,
        "requires_arabic_legal_precision": profile.requires_arabic_legal_precision,
        "requires_code_execution": profile.requires_code_execution,
        "requires_multimodal": profile.requires_multimodal,
        "requires_citations": profile.requires_citations,
    }


def build_audited_execution_plan(
    task: str,
    tenant_id: str | None = None,
    *,
    subject_id: str | None = None,
    actor_id: str = "qarar-router",
    sink: QalaAuditSink | None = None,
    trace: QalaTraceContext | None = None,
) -> ExecutionPlan:
    """Build an execution plan and record the decision in the sealed sink.

    Reuses the pure ``build_execution_plan`` as the single source of plan
    construction; this wrapper only adds the audit side effect. ``actor_id``
    is recorded for provenance; ``subject_id`` defaults to the trace id.
    """
    audit_tenant = tenant_id or _DEFAULT_TENANT
    sink = sink if sink is not None else QalaAuditSink()
    ctx = trace if trace is not None else new_trace(audit_tenant, _ROUTING_PHASE)
    subject = subject_id or ctx.trace_id

    profile = classify_task(task, tenant_id=tenant_id)
    classification_payload = _profile_payload(profile, subject)
    classification_payload["actor_id"] = actor_id
    _require_ok(
        sink.append(
            event="classification_decision",
            trace_id=ctx.trace_id,
            span_id=ctx.span_id,
            tenant_id=audit_tenant,
            payload=classification_payload,
        )
    )

    try:
        plan = build_execution_plan(task, tenant_id=tenant_id)
    except ValueError as exc:
        _require_ok(
            sink.append(
                event="route_blocked",
                trace_id=ctx.trace_id,
                span_id=ctx.span_id,
                tenant_id=audit_tenant,
                payload={
                    "subject_id": subject,
                    "actor_id": actor_id,
                    "kind": profile.kind.value,
                    "risk": profile.risk,
                    "reason": str(exc),
                },
            )
        )
        raise

    route = plan.route
    _require_ok(
        sink.append(
            event="route_decision",
            trace_id=ctx.trace_id,
            span_id=ctx.span_id,
            tenant_id=audit_tenant,
            payload={
                "subject_id": subject,
                "actor_id": actor_id,
                "primary_agent_id": plan.primary_agent_id,
                "provider": route.provider,
                "model": route.model,
                "requires_reviewer": route.requires_reviewer,
                "reviewer_agent_id": route.reviewer_agent_id,
                "validation_required": plan.validation_required,
                "steps": list(plan.steps),
            },
        )
    )

    return plan


__all__ = ["AuditError", "build_audited_execution_plan"]
