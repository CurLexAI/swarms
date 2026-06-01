# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Audited wrapper around the sovereign local-only model router."""

from __future__ import annotations

import importlib.util
import sys
import uuid
from collections.abc import Mapping
from typing import Any, Literal, Protocol, cast
from pathlib import Path
from pydantic import BaseModel, Field

from src.policy.sovereign.classification import DataClassification
from src.policy.sovereign.model_router import ProviderMap, RouteDecision, route

AuditAction = Literal["classification_decision", "route_decision", "route_blocked"]


class AuditChainBrokenError(RuntimeError):
    """Raised when audit append or hash-chain validation fails closed."""


class AuditSink(Protocol):
    """Protocol for append-only audit sinks used by the router."""

    def append(
        self,
        *,
        event: str,
        trace_id: str,
        span_id: str,
        tenant_id: str,
        payload: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> Any:
        """Append an audit record and return the sink-specific result."""


class AuditValidator(Protocol):
    """Protocol for hash-chain validators used after every router audit."""

    def verify_chain(self) -> Any:
        """Verify the audit chain and return a sink-specific result."""


class AuditedExecutionPlan(BaseModel):
    """Audited router response returned to callers."""

    subject_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    route: RouteDecision


class QalaAuditAdapter:
    """Adapter that loads and reuses the existing Qala audit sink."""

    def __init__(self) -> None:
        sink_cls = _load_qala_audit_sink_class()
        self._sink = sink_cls()

    def append(
        self,
        *,
        event: str,
        trace_id: str,
        span_id: str,
        tenant_id: str,
        payload: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> Any:
        """Append to the existing Qala sink."""

        return self._sink.append(
            event=event,
            trace_id=trace_id,
            span_id=span_id,
            tenant_id=tenant_id,
            payload=payload,
            occurred_at=occurred_at,
        )

    def verify_chain(self) -> Any:
        """Verify the existing Qala sink hash chain."""

        return self._sink.verify_chain()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_qala_audit_sink_class() -> type[Any]:
    sink_path = _repo_root() / ".agents" / "validators" / "qala_audit_sink.py"
    spec = importlib.util.spec_from_file_location("_qala_audit_sink_runtime", sink_path)
    if spec is None or spec.loader is None:
        raise AuditChainBrokenError("AUDIT_CHAIN_BROKEN: Qala audit sink loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    sink_cls = getattr(module, "QalaAuditSink", None)
    if sink_cls is None:
        raise AuditChainBrokenError("AUDIT_CHAIN_BROKEN: QalaAuditSink unavailable")
    return cast(type[Any], sink_cls)


def _assert_audit_ok(result: Any, context: str) -> None:
    ok = getattr(result, "ok", False)
    if ok is not True:
        error = getattr(result, "error", "AUDIT_CHAIN_BROKEN")
        raise AuditChainBrokenError(f"AUDIT_CHAIN_BROKEN: {context}: {error}")


def _route_payload(action: AuditAction, decision: RouteDecision) -> dict[str, object]:
    return {
        "action": action,
        "classification": decision.classification.value if decision.classification else "UNKNOWN",
        "provider_selected": decision.provider_selected,
        "status": decision.status,
        "blocked_reason": decision.blocked_reason,
        "message_ar": "تم تسجيل قرار التوجيه السيادي في سلسلة التدقيق.",
    }


def _append_and_verify(
    *,
    audit_sink: AuditSink,
    audit_validator: AuditValidator,
    action: AuditAction,
    trace_id: str,
    tenant_id: str,
    payload: Mapping[str, Any],
) -> None:
    append_result = audit_sink.append(
        event="policy_decision",
        trace_id=trace_id,
        span_id=f"model_router.{action}",
        tenant_id=tenant_id,
        payload=payload,
    )
    _assert_audit_ok(append_result, f"append {action}")
    verify_result = audit_validator.verify_chain()
    _assert_audit_ok(verify_result, f"verify {action}")


async def build_audited_execution_plan(
    query: str,
    classification: DataClassification | str,
    subject_id: str,
    *,
    max_tokens: int = 512,
    providers: ProviderMap | None = None,
    audit_sink: AuditSink | None = None,
    audit_validator: AuditValidator | None = None,
) -> AuditedExecutionPlan:
    """Build an audited local-model execution plan.

    Args:
        query: Prompt/query to route to a local model runtime.
        classification: Data classification controlling provider eligibility.
        subject_id: Tenant or subject identifier used for audit tenancy.
        max_tokens: Maximum generated tokens.
        providers: Optional injected local providers.
        audit_sink: Optional injected audit sink for tests.
        audit_validator: Optional injected audit-chain validator for tests.

    Returns:
        Audited execution plan with a completed or blocked route decision.

    Raises:
        AuditChainBrokenError: If any audit append or verification step fails.
    """

    if len(subject_id.strip()) == 0:
        raise ValueError("subject_id is required")

    trace_id = str(uuid.uuid4())
    normalized_classification: DataClassification | str
    try:
        _dc = DataClassification(str(classification).upper())
        classification_value = _dc.value
        normalized_classification = _dc
    except ValueError:
        normalized_classification = str(classification)
        classification_value = "UNKNOWN"

    default_adapter = QalaAuditAdapter() if audit_sink is None else None
    sink: AuditSink = audit_sink if audit_sink is not None else cast(AuditSink, default_adapter)
    validator: AuditValidator = (
        audit_validator
        if audit_validator is not None
        else cast(AuditValidator, sink)
    )

    _append_and_verify(
        audit_sink=sink,
        audit_validator=validator,
        action="classification_decision",
        trace_id=trace_id,
        tenant_id=subject_id,
        payload={
            "action": "classification_decision",
            "classification": classification_value,
            "message_ar": "تم اعتماد تصنيف البيانات قبل اختيار مزود الاستدلال المحلي.",
        },
    )

    decision = await route(
        normalized_classification,
        query,
        max_tokens=max_tokens,
        providers=providers,
    )
    action: AuditAction = "route_blocked" if decision.status == "BLOCKED" else "route_decision"
    _append_and_verify(
        audit_sink=sink,
        audit_validator=validator,
        action=action,
        trace_id=trace_id,
        tenant_id=subject_id,
        payload=_route_payload(action, decision),
    )

    return AuditedExecutionPlan(subject_id=subject_id, trace_id=trace_id, route=decision)
