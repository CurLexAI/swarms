# SPDX-License-Identifier: MIT
# Licensed under MIT
"""SAMA regulatory ingestion swarm package.

The package is intentionally adapter-driven: agents accept object-store,
security-gate, vector, text-index, ticket, and audit ports by dependency
injection so production wiring can remain private and tests can use mocks.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core.audited_router import AuditChainBrokenError, QalaAuditAdapter


def record_audit_event(
    *,
    action: str,
    trace_id: str,
    tenant_id: str,
    payload: Mapping[str, Any],
    audit: QalaAuditAdapter | None = None,
) -> None:
    """Append and verify a SAMA swarm audit event.

    Args:
        action: Stable event action stored in the audit payload.
        trace_id: Trace identifier for this pipeline run.
        tenant_id: Tenant/subject identifier.
        payload: Sanitized JSON-compatible payload.
        audit: Optional injected Qala adapter.

    Raises:
        AuditChainBrokenError: If appending or verifying the audit chain fails.
    """

    adapter = audit or QalaAuditAdapter()
    event_payload: dict[str, Any] = {"action": action, **dict(payload)}
    append_result = adapter.append(
        event="policy_decision",
        trace_id=trace_id,
        span_id=f"sama_ingestion.{action}",
        tenant_id=tenant_id,
        payload=event_payload,
    )
    if getattr(append_result, "ok", False) is not True:
        error = getattr(append_result, "error", "AUDIT_CHAIN_BROKEN")
        raise AuditChainBrokenError(f"AUDIT_CHAIN_BROKEN: append {action}: {error}")
    verify_result = adapter.verify_chain()
    if getattr(verify_result, "ok", False) is not True:
        error = getattr(verify_result, "error", "AUDIT_CHAIN_BROKEN")
        raise AuditChainBrokenError(f"AUDIT_CHAIN_BROKEN: verify {action}: {error}")
