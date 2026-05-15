"""Qal'a (قلعة) — Q6 Trace & Correlation (Python side).

Pure, dependency-free trace context for the Qal'a security layer.
No network calls. No persistent state. No background workers.

Secrets and raw PII MUST NOT enter this module — its outputs are
transported as headers and logged into the sealed audit sink.

Mirror of ``src/security/qalaTrace.ts``. See
``docs/decisions/ADR-0003-qala-security-architecture.md`` §Q6.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Final, Literal, Mapping

QalaPhase = Literal[
    "auth_check",
    "input_validation",
    "policy_check",
    "egress_check",
    "model_call",
    "output_validation",
    "audit_emit",
]

_QALA_PHASES: Final[frozenset[str]] = frozenset(
    {
        "auth_check",
        "input_validation",
        "policy_check",
        "egress_check",
        "model_call",
        "output_validation",
        "audit_emit",
    }
)

_UUID_V4_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_MAX_TENANT_ID_LENGTH: Final[int] = 128
_TENANT_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class QalaTraceError(ValueError):
    """Raised when a trace context cannot be constructed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class QalaTraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    tenant_id: str
    phase: QalaPhase
    started_at: str


HEADER_TRACE_ID: Final[str] = "x-qala-trace-id"
HEADER_SPAN_ID: Final[str] = "x-qala-span-id"
HEADER_PARENT_SPAN_ID: Final[str] = "x-qala-parent-span-id"
HEADER_TENANT_ID: Final[str] = "x-qala-tenant-id"
HEADER_PHASE: Final[str] = "x-qala-phase"
HEADER_STARTED_AT: Final[str] = "x-qala-started-at"


def _validate_tenant_id(tenant_id: str) -> None:
    if not isinstance(tenant_id, str) or len(tenant_id) == 0:
        raise QalaTraceError("INVALID_TENANT_ID", "tenant_id must be a non-empty string")
    if len(tenant_id) > _MAX_TENANT_ID_LENGTH:
        raise QalaTraceError(
            "INVALID_TENANT_ID",
            f"tenant_id exceeds max length ({_MAX_TENANT_ID_LENGTH})",
        )
    if not _TENANT_ID_PATTERN.fullmatch(tenant_id):
        raise QalaTraceError(
            "INVALID_TENANT_ID", "tenant_id must match [A-Za-z0-9_-]{1,128}"
        )


def _validate_phase(phase: str) -> QalaPhase:
    if phase not in _QALA_PHASES:
        raise QalaTraceError("INVALID_PHASE", f"unknown phase: {phase!r}")
    return phase  # type: ignore[return-value]


def _now_iso() -> str:
    # UTC, second resolution. Avoid microseconds so the round-trip stays compact
    # in headers. The sealed audit sink stamps its own occurred_at separately.
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def new_trace(tenant_id: str, phase: str) -> QalaTraceContext:
    _validate_tenant_id(tenant_id)
    validated_phase = _validate_phase(phase)
    return QalaTraceContext(
        trace_id=str(uuid.uuid4()),
        span_id=str(uuid.uuid4()),
        parent_span_id=None,
        tenant_id=tenant_id,
        phase=validated_phase,
        started_at=_now_iso(),
    )


def child_span(parent: QalaTraceContext, phase: str) -> QalaTraceContext:
    validated_phase = _validate_phase(phase)
    return replace(
        parent,
        span_id=str(uuid.uuid4()),
        parent_span_id=parent.span_id,
        phase=validated_phase,
        started_at=_now_iso(),
    )


def to_headers(ctx: QalaTraceContext) -> dict[str, str]:
    """Serialize trace context to outbound headers.

    tenant_id IS permitted in headers per ADR-0003 §Q6 — it is required
    for cross-hop correlation and is not classified as secret material.
    Secrets and PII MUST NOT appear in any value.
    """
    headers: dict[str, str] = {
        HEADER_TRACE_ID: ctx.trace_id,
        HEADER_SPAN_ID: ctx.span_id,
        HEADER_TENANT_ID: ctx.tenant_id,
        HEADER_PHASE: ctx.phase,
        HEADER_STARTED_AT: ctx.started_at,
    }
    if ctx.parent_span_id is not None:
        headers[HEADER_PARENT_SPAN_ID] = ctx.parent_span_id
    return headers


def _read_header(headers: Mapping[str, str], name: str) -> str | None:
    direct = headers.get(name)
    if isinstance(direct, str) and len(direct) > 0:
        return direct
    target = name.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == target:
            if isinstance(value, str) and len(value) > 0:
                return value
    return None


def from_headers(headers: Mapping[str, str]) -> QalaTraceContext | None:
    """Best-effort, fail-closed reader. Returns None when any required
    header is missing or any value is malformed.

    Never raises on missing/malformed headers — callers branch on None.
    """
    trace_id = _read_header(headers, HEADER_TRACE_ID)
    span_id = _read_header(headers, HEADER_SPAN_ID)
    tenant_id = _read_header(headers, HEADER_TENANT_ID)
    phase = _read_header(headers, HEADER_PHASE)
    started_at = _read_header(headers, HEADER_STARTED_AT)
    parent_span_id = _read_header(headers, HEADER_PARENT_SPAN_ID)

    if (
        trace_id is None
        or span_id is None
        or tenant_id is None
        or phase is None
        or started_at is None
    ):
        return None

    if not _UUID_V4_PATTERN.fullmatch(trace_id):
        return None
    if not _UUID_V4_PATTERN.fullmatch(span_id):
        return None
    if parent_span_id is not None and not _UUID_V4_PATTERN.fullmatch(parent_span_id):
        return None

    if phase not in _QALA_PHASES:
        return None

    try:
        _validate_tenant_id(tenant_id)
    except QalaTraceError:
        return None

    # Permissive ISO-8601 parse — accept "Z" suffix.
    try:
        datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return None

    return QalaTraceContext(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        tenant_id=tenant_id,
        phase=phase,  # type: ignore[arg-type]
        started_at=started_at,
    )


__all__ = [
    "QalaPhase",
    "QalaTraceContext",
    "QalaTraceError",
    "new_trace",
    "child_span",
    "to_headers",
    "from_headers",
    "HEADER_TRACE_ID",
    "HEADER_SPAN_ID",
    "HEADER_PARENT_SPAN_ID",
    "HEADER_TENANT_ID",
    "HEADER_PHASE",
    "HEADER_STARTED_AT",
]
