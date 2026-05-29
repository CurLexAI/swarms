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
    metadata: dict[str, object] = Field(default_factory=dict)


_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_KSA_ID_RE = re.compile(r"(?<!\d)[12]\d{9}(?!\d)")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?966\s?5\d{8}|05\d{8})(?!\d)")
_IBAN_RE = re.compile(r"\bSA\d{22}\b", re.IGNORECASE)
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_BEARER_RE = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE)
_API_KEY_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{12,}"
)
_SECURITY_RE = re.compile(r"(?i)\b(?:password|private key|credential|exploit|vulnerability)\b")


def _public_source_allowlist() -> frozenset[str]:
    configured = os.environ.get("SAMA_ALLOWED_DOMAINS", "www.sama.gov.sa,sama.gov.sa")
    return frozenset(host.strip().lower() for host in configured.split(",") if host.strip())


def _source_domain(source: str) -> str:
    parsed = urlparse(source)
    host = parsed.hostname if parsed.hostname else source.split("/", 1)[0]
    return host.lower().strip()


def _detect_sensitive_signals(text_sample: str) -> tuple[str, ...]:
    signals: list[str] = []
    checks: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("ksa_id_or_iqama", _KSA_ID_RE),
        ("email", _EMAIL_RE),
        ("phone", _PHONE_RE),
        ("iban", _IBAN_RE),
        ("private_key", _PRIVATE_KEY_RE),
        ("bearer_token", _BEARER_RE),
        ("api_key_or_secret", _API_KEY_RE),
        ("security_sensitive", _SECURITY_RE),
    )
    for label, pattern in checks:
        if pattern.search(text_sample):
            signals.append(label)
    return tuple(signals)


def classify_content(
    source: str,
    text_sample: str,
    metadata: dict[str, object],
) -> ClassificationDecision:
    """Classify content for sovereign routing and ingestion.

    Args:
        source: Source URL or domain.
        text_sample: Text sample to inspect for sensitive signals.
        metadata: Caller-supplied metadata to preserve with the decision.

    Returns:
        Classification decision. PUBLIC is assigned only for explicitly
        allowlisted public/regulatory domains with no sensitive signals;
        uncertain content defaults to INTERNAL.
    """

    domain = _source_domain(source)
    signals = _detect_sensitive_signals(text_sample)
    allowlisted = domain in _public_source_allowlist()

    if any(signal in signals for signal in ("private_key", "bearer_token", "api_key_or_secret")):
        return ClassificationDecision(
            classification=DataClassification.RESTRICTED,
            source=source,
            reasons=("secret_or_credential_detected",),
            detected_signals=signals,
            metadata=metadata,
        )

    if signals:
        return ClassificationDecision(
            classification=DataClassification.CONFIDENTIAL,
            source=source,
            reasons=("pii_or_security_sensitive_signal_detected",),
            detected_signals=signals,
            metadata=metadata,
        )

    if allowlisted:
        return ClassificationDecision(
            classification=DataClassification.PUBLIC,
            source=source,
            reasons=("allowlisted_public_regulatory_source",),
            detected_signals=signals,
            metadata=metadata,
        )

    return ClassificationDecision(
        classification=DataClassification.INTERNAL,
        source=source,
        reasons=("default_internal_when_uncertain",),
        detected_signals=signals,
        metadata=metadata,
    )
