# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Data classification primitives for sovereign model routing and ingestion."""

from __future__ import annotations

import os
import re
from enum import StrEnum
from urllib.parse import urlparse

from pydantic import BaseModel, Field


class DataClassification(StrEnum):
    """Supported Qarar data classification labels."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class ClassificationDecision(BaseModel):
    """Decision returned by the sovereign content classifier."""

    classification: DataClassification
    source: str = Field(min_length=1)
    reasons: tuple[str, ...]
    detected_signals: tuple[str, ...] = ()
    decision_trace: tuple[str, ...] = ()
    metadata: dict[str, object] = Field(default_factory=dict)


_CLASSIFICATION_RANK: dict[DataClassification, int] = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.CONFIDENTIAL: 2,
    DataClassification.RESTRICTED: 3,
}
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_KSA_ID_RE = re.compile(r"(?<!\d)[12]\d{9}(?!\d)")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?9665\d{8}|05\d{8})(?!\d)")
_CREDIT_CARD_RE = re.compile(r"(?<!\d)\d{16}(?!\d)")
_PASSPORT_RE = re.compile(r"\b[A-Z]{2}\d{6}\b")
_IBAN_RE = re.compile(r"\bSA\d{22}\b", re.IGNORECASE)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)
_API_KEY_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{12,}"
)
_SECURITY_RE = re.compile(r"(?i)\b(?:password|private key|credential|exploit|vulnerability)\b")


def _public_source_allowlist() -> frozenset[str]:
    """Return exact public-source hostnames allowed to remain PUBLIC."""

    configured = os.environ.get(
        "SAMA_ALLOWED_DOMAINS",
        ",".join(
            (
                "sama.gov.sa",
                "www.sama.gov.sa",
                "cma.org.sa",
                "www.cma.org.sa",
                "mof.gov.sa",
                "www.mof.gov.sa",
                "mci.gov.sa",
                "www.mci.gov.sa",
                "ncc.gov.sa",
                "www.ncc.gov.sa",
            )
        ),
    )
    return frozenset(host.strip().lower() for host in configured.split(",") if host.strip())


def _source_domain(source: str) -> str:
    """Extract a normalized hostname without substring trust."""

    candidate = source.strip()
    parsed = urlparse(candidate)
    if parsed.hostname is None and "://" not in candidate:
        parsed = urlparse(f"//{candidate}")
    host = parsed.hostname if parsed.hostname else candidate.split("/", 1)[0]
    return host.lower().strip("[] ")


def _normalize_text(text_sample: str) -> str:
    """Normalize separators that commonly hide PII patterns."""

    return re.sub(r"[\s-]+", "", text_sample)


def _detect_sensitive_signals(text_sample: str) -> tuple[str, ...]:
    """Detect sensitive categories without returning raw matched values."""

    normalized = _normalize_text(text_sample)
    signals: list[str] = []
    checks: tuple[tuple[str, re.Pattern[str], str], ...] = (
        ("ksa_id_or_iqama", _KSA_ID_RE, normalized),
        ("email", _EMAIL_RE, text_sample),
        ("phone", _PHONE_RE, normalized),
        ("credit_card_shape", _CREDIT_CARD_RE, normalized),
        ("passport_shape", _PASSPORT_RE, normalized),
        ("iban", _IBAN_RE, normalized),
        ("private_key", _PRIVATE_KEY_RE, text_sample),
        ("bearer_token", _BEARER_RE, text_sample),
        ("api_key_or_secret", _API_KEY_RE, text_sample),
        ("security_sensitive", _SECURITY_RE, text_sample),
    )
    for label, pattern, haystack in checks:
        if pattern.search(haystack):
            signals.append(label)
    return tuple(signals)


def _metadata_classification(
    metadata: dict[str, object],
) -> tuple[DataClassification | None, str | None]:
    """Return explicit metadata escalation, if one is present and valid."""

    if metadata.get("restricted") is True:
        return DataClassification.RESTRICTED, "metadata_restricted_true"
    if str(metadata.get("sensitivity", "")).lower() == "high":
        return DataClassification.CONFIDENTIAL, "metadata_sensitivity_high"
    floor = metadata.get("classification_floor")
    if isinstance(floor, str):
        try:
            return DataClassification(floor.upper()), "metadata_classification_floor"
        except ValueError:
            return None, "metadata_classification_floor_invalid"
    return None, None


def _max_classification(*values: DataClassification) -> DataClassification:
    """Return the most restrictive classification by sovereign precedence."""

    return max(values, key=lambda value: _CLASSIFICATION_RANK[value])


def classify_content(
    source: str,
    text_sample: str | None = None,
    metadata: dict[str, object] | None = None,
) -> ClassificationDecision:
    """Classify content for sovereign routing and ingestion.

    Args:
        source: Source URL or domain.
        text_sample: Optional text sample to inspect for sensitive signals.
        metadata: Optional caller-supplied metadata preserved with the decision.

    Returns:
        Classification decision. PUBLIC is assigned only for exact allowlisted
        public/regulatory hostnames with no sensitive signals or metadata
        escalation; uncertain content defaults to INTERNAL.
    """

    safe_metadata = dict(metadata or {})
    sample = text_sample or ""
    domain = _source_domain(source)
    signals = _detect_sensitive_signals(sample) if sample else ()
    allowlisted = domain in _public_source_allowlist()
    reasons: list[str] = []
    trace: list[str] = ["precedence:RESTRICTED>CONFIDENTIAL>INTERNAL>PUBLIC"]

    base_classification = DataClassification.PUBLIC if allowlisted else DataClassification.INTERNAL
    if allowlisted:
        reasons.append("allowlisted_public_regulatory_source")
        trace.append(f"source_hostname_allowlisted:{domain}")
    else:
        reasons.append("default_internal_when_uncertain")
        trace.append(f"source_hostname_not_allowlisted:{domain}")

    if any(signal in signals for signal in ("private_key", "bearer_token", "api_key_or_secret")):
        reasons.append("secret_or_credential_detected")
        trace.append("sensitive_signal_escalation:RESTRICTED")
        signal_classification = DataClassification.RESTRICTED
    elif signals:
        reasons.append("pii_or_security_sensitive_signal_detected")
        trace.append("sensitive_signal_escalation:CONFIDENTIAL")
        signal_classification = DataClassification.CONFIDENTIAL
    else:
        signal_classification = base_classification
        trace.append("sensitive_signal_escalation:none")

    metadata_classification, metadata_reason = _metadata_classification(safe_metadata)
    if metadata_reason is not None:
        reasons.append(metadata_reason)
        metadata_trace_value = (
            metadata_classification.value if metadata_classification else "ignored"
        )
        trace.append(f"metadata_escalation:{metadata_trace_value}")
    else:
        trace.append("metadata_escalation:none")

    classification = _max_classification(
        base_classification,
        signal_classification,
        metadata_classification or base_classification,
    )
    trace.append(f"final_classification:{classification.value}")

    return ClassificationDecision(
        classification=classification,
        source=source,
        reasons=tuple(dict.fromkeys(reasons)),
        detected_signals=signals,
        decision_trace=tuple(trace),
        metadata=safe_metadata,
    )
