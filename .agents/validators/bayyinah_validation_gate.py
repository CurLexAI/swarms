# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Bayyinah validation gate.

This gate enforces policy before a generated output can be treated as safe. It
is deterministic and can run without Modal. If Modal Bayyinah is configured, a
caller may additionally ask Bayyinah for a model-based critique before final
approval.
"""

from __future__ import annotations

from typing import Any

from ..router.types import TaskProfile, ValidationFinding, ValidationReport


_HIGH_RISK_SEVERITIES = {"HIGH", "CRITICAL"}
_REGULATORY_TERMS = ("SAMA", "PDPL", "NCA", "compliant", "امتثال", "ساما", "نظام حماية البيانات")
_PROMPT_INJECTION_TERMS = (
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "leak token",
    "bypass policy",
    "تجاهل التعليمات",
)
# Bare "http://" / "https://" are not listed: they appear in legitimate
# citation URLs and would block any output that cites a source. Only patterns
# that imply *executing* a network call are flagged here.
_NETWORK_TERMS = ("curl ", "wget ", "requests.post", "fetch(", "urllib.request")


def validate_output(
    *,
    output: Any,
    profile: TaskProfile,
    validation_evidence: str | None = None,
    citations: tuple[str, ...] = (),
    tenant_id: str | None = None,
    bayyinah_findings: tuple[ValidationFinding, ...] = (),
) -> ValidationReport:
    findings: list[ValidationFinding] = list(bayyinah_findings)
    text = _to_text(output)

    if profile.tenant_id and tenant_id and profile.tenant_id != tenant_id:
        findings.append(
            ValidationFinding(
                severity="CRITICAL",
                category="TENANT_ISOLATION",
                message="Output tenant_id does not match task tenant_id.",
            )
        )

    if profile.requires_citations and not citations:
        findings.append(
            ValidationFinding(
                severity="HIGH",
                category="CITATION",
                message="Task requires citations but no citations were supplied.",
            )
        )

    if profile.requires_code_execution and not validation_evidence:
        findings.append(
            ValidationFinding(
                severity="MEDIUM",
                category="CODE_CORRECTNESS",
                message="Code-related task lacks validation evidence such as typecheck, tests, or syntax check.",
            )
        )

    if profile.requires_arabic_legal_precision and _contains_regulatory_claim(text) and not citations:
        findings.append(
            ValidationFinding(
                severity="CRITICAL",
                category="LEGAL_ACCURACY",
                message="Arabic/legal or regulatory claim was made without evidence.",
            )
        )

    if _contains_prompt_injection(text):
        findings.append(
            ValidationFinding(
                severity="HIGH",
                category="PROMPT_INJECTION",
                message="Output contains prompt-injection language that must not be propagated as instructions.",
            )
        )

    if _contains_unauthorized_network_pattern(text):
        findings.append(
            ValidationFinding(
                severity="HIGH",
                category="POLICY",
                message="Output contains network execution patterns requiring explicit authorization.",
            )
        )

    if any(f.severity == "CRITICAL" for f in findings):
        return ValidationReport(verdict="BLOCKED", severity="critical", findings=tuple(findings), safe_output=None)
    if any(f.severity in _HIGH_RISK_SEVERITIES for f in findings):
        return ValidationReport(verdict="BLOCKED", severity="high", findings=tuple(findings), safe_output=None)
    if findings:
        return ValidationReport(verdict="REQUEST_CHANGES", severity="medium", findings=tuple(findings), safe_output=output)
    return ValidationReport(verdict="APPROVE", severity="none", findings=(), safe_output=output)


def _to_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    return repr(output)


def _contains_regulatory_claim(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in _REGULATORY_TERMS)


def _contains_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _PROMPT_INJECTION_TERMS)


def _contains_unauthorized_network_pattern(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _NETWORK_TERMS)
