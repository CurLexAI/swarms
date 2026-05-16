"""Qal'a (قلعة) — Q3 Input-side validation gate.

Mirror of ``bayyinah_validation_gate.validate_output`` but applied to
the *prompt* before any model is invoked. Verdict contract is identical
(``APPROVE | REQUEST_CHANGES | BLOCKED``) so callers can branch
uniformly. Fail-closed: any uncertainty returns ``BLOCKED``.

Checks (per ADR-0003 §Q3):

- Payload shape (non-empty dict with required ``tenant_id`` + ``input``).
- Prompt-injection phrase set (Arabic + English).
- KSA-PII via :mod:`qala_ksa_pii`.
- Unauthorized network-execution patterns.
- Excessive input length (consistent with adapter ``MAX_INPUT_LENGTH``).
- Tenant identifier match when ``TaskProfile.tenant_id`` is set.

No model invocation. No network calls. Pure function.

See ``docs/decisions/ADR-0003-qala-security-architecture.md`` §Q3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal, Mapping

from ..router.types import TaskProfile, ValidationFinding, ValidationReport
from . import qala_ksa_pii

# Phrase sets shared with bayyinah_validation_gate. Duplicated here on
# purpose: the input gate is a stand-alone fail-closed barrier and must
# not import from the post-hoc gate (avoids a hard coupling that would
# block either side from evolving independently).
_PROMPT_INJECTION_TERMS: Final[tuple[str, ...]] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "system prompt",
    "developer message",
    "leak token",
    "bypass policy",
    "reveal the system prompt",
    "تجاهل التعليمات",
)

_NETWORK_TERMS: Final[tuple[str, ...]] = (
    "curl ",
    "wget ",
    "requests.post",
    "requests.get",
    "fetch(",
    "urllib.request",
    "xmlhttprequest",
)

MAX_INPUT_LENGTH: Final[int] = 8000
MAX_TENANT_ID_LENGTH: Final[int] = 128

_HIGH_RISK_SEVERITIES: Final[frozenset[str]] = frozenset({"HIGH", "CRITICAL"})


@dataclass(frozen=True)
class InputPayload:
    """Caller-supplied payload validated by the gate.

    Mirrors the four-field allowlist of ``unifiedAgentAdapter``.
    Additional fields are rejected by ``_validate_shape``.
    """

    tenant_id: str
    input: str
    metadata: Mapping[str, Any] | None = None
    context: Mapping[str, Any] | None = None


def validate_input(
    *,
    payload: Mapping[str, Any] | InputPayload,
    profile: TaskProfile,
) -> ValidationReport:
    """Validate a prompt payload before model invocation.

    Returns a ``ValidationReport`` whose ``verdict`` is one of
    ``APPROVE | REQUEST_CHANGES | BLOCKED``. Fail-closed: any CRITICAL
    finding yields ``BLOCKED`` with ``severity='critical'`` and a
    ``safe_output=None``.
    """
    shape_findings, normalized = _validate_shape(payload)
    if any(f.severity == "CRITICAL" for f in shape_findings):
        # Shape failures preempt further checks because subsequent
        # checks assume tenant_id and input are present and string.
        return ValidationReport(
            verdict="BLOCKED",
            severity="critical",
            findings=tuple(shape_findings),
            safe_output=None,
        )

    assert normalized is not None  # narrowed by shape check above

    findings: list[ValidationFinding] = list(shape_findings)

    if profile.tenant_id is not None and profile.tenant_id != normalized.tenant_id:
        findings.append(
            ValidationFinding(
                severity="CRITICAL",
                category="TENANT_ISOLATION",
                message="Payload tenant_id does not match task profile tenant_id.",
            )
        )

    if len(normalized.input) > MAX_INPUT_LENGTH:
        findings.append(
            ValidationFinding(
                severity="HIGH",
                category="POLICY",
                message=f"input exceeds Q3 length limit ({MAX_INPUT_LENGTH})",
            )
        )

    if _contains_prompt_injection(normalized.input):
        findings.append(
            ValidationFinding(
                severity="HIGH",
                category="PROMPT_INJECTION",
                message=(
                    "Input contains prompt-injection language that must not "
                    "be propagated as instructions."
                ),
            )
        )

    if _contains_unauthorized_network_pattern(normalized.input):
        findings.append(
            ValidationFinding(
                severity="HIGH",
                category="POLICY",
                message=(
                    "Input contains network execution patterns requiring "
                    "explicit authorization."
                ),
            )
        )

    pii_hits = qala_ksa_pii.detect_ksa_pii(normalized.input)
    if pii_hits:
        categories = sorted({h.category for h in pii_hits})
        findings.append(
            ValidationFinding(
                severity="CRITICAL",
                category="POLICY",
                message=(
                    "Input contains sovereign KSA identifiers and must be "
                    f"redacted before model invocation: {','.join(categories)}"
                ),
            )
        )

    verdict, severity, safe_output = _resolve_verdict(findings, normalized)
    return ValidationReport(
        verdict=verdict,
        severity=severity,
        findings=tuple(findings),
        safe_output=safe_output,
    )


_VerdictTriple = tuple[
    Literal["APPROVE", "REQUEST_CHANGES", "BLOCKED"],
    Literal["none", "low", "medium", "high", "critical"],
    Any,
]


def _resolve_verdict(
    findings: list[ValidationFinding], normalized: InputPayload
) -> _VerdictTriple:
    if any(f.severity == "CRITICAL" for f in findings):
        return ("BLOCKED", "critical", None)
    if any(f.severity in _HIGH_RISK_SEVERITIES for f in findings):
        return ("BLOCKED", "high", None)
    if findings:
        return ("REQUEST_CHANGES", "medium", normalized)
    return ("APPROVE", "none", normalized)


_ALLOWED_PAYLOAD_FIELDS: Final[frozenset[str]] = frozenset(
    {"tenant_id", "input", "metadata", "context"}
)


def _validate_shape(
    payload: Any,
) -> tuple[list[ValidationFinding], InputPayload | None]:
    if isinstance(payload, InputPayload):
        # The dataclass shape is already enforced; do a length check only.
        return ([], payload)

    if payload is None or not isinstance(payload, Mapping):
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message="payload must be a mapping",
                )
            ],
            None,
        )

    unknown = sorted(set(payload.keys()) - _ALLOWED_PAYLOAD_FIELDS)
    if unknown:
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message=f"payload contains unknown fields: {','.join(unknown)}",
                )
            ],
            None,
        )

    tenant_id = payload.get("tenant_id")
    input_value = payload.get("input")

    if not isinstance(tenant_id, str) or len(tenant_id.strip()) == 0:
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message="tenant_id is required and must be a non-empty string",
                )
            ],
            None,
        )
    if len(tenant_id) > MAX_TENANT_ID_LENGTH:
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message=f"tenant_id exceeds max length ({MAX_TENANT_ID_LENGTH})",
                )
            ],
            None,
        )
    if not isinstance(input_value, str) or len(input_value.strip()) == 0:
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message="input is required and must be a non-empty string",
                )
            ],
            None,
        )

    metadata = payload.get("metadata")
    context = payload.get("context")
    if metadata is not None and not isinstance(metadata, Mapping):
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message="metadata must be a mapping when provided",
                )
            ],
            None,
        )
    if context is not None and not isinstance(context, Mapping):
        return (
            [
                ValidationFinding(
                    severity="CRITICAL",
                    category="POLICY",
                    message="context must be a mapping when provided",
                )
            ],
            None,
        )

    return (
        [],
        InputPayload(
            tenant_id=tenant_id.strip(),
            input=input_value,
            metadata=metadata,
            context=context,
        ),
    )


def _contains_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in _PROMPT_INJECTION_TERMS)


def _contains_unauthorized_network_pattern(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _NETWORK_TERMS)


__all__ = [
    "InputPayload",
    "MAX_INPUT_LENGTH",
    "MAX_TENANT_ID_LENGTH",
    "validate_input",
]
