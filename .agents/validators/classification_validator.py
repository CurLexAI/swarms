# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Data classification validator (sovereign content tiering).

Assigns a coarse data-classification tier to a piece of content based on
its declared source and on KSA-PII presence (reusing the Q5 detector in
``qala_ksa_pii``). Classification decisions can be recorded to the Q7
sealed audit sink via the ``classification_decision`` event.

This is a deterministic, offline heuristic — no network calls, no
persistent state, no background workers. It is an operational aid for
routing/handling, **not** a regulatory-compliance determination (SAMA /
PDPL / NCA classification is a governed process and is out of scope for
this module). Audit payloads carry only PII *category names*, never raw
or masked values, so they are safe to seal directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .qala_ksa_pii import detect_ksa_pii


class DataClassification(Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


# Ordered from least to most sensitive; index doubles as the rank used
# for monotonic escalation (a classification never downgrades).
_ORDER: tuple[DataClassification, ...] = (
    DataClassification.PUBLIC,
    DataClassification.INTERNAL,
    DataClassification.CONFIDENTIAL,
    DataClassification.RESTRICTED,
)

# Allowlisted sovereign public sources (token match, case-insensitive).
# Content declared from one of these is treated as PUBLIC unless escalated
# by PII detection or an explicit metadata floor.
PUBLIC_SOURCE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "sama",  # Saudi Central Bank
        "nca",  # National Cybersecurity Authority
        "zatca",  # Zakat, Tax and Customs Authority
        "mci",  # Ministry of Commerce
        "mcit",  # Ministry of Communications and IT
        "moj",  # Ministry of Justice
        "boe",  # Bureau of Experts (laws.boe.gov.sa)
        "spa",  # Saudi Press Agency
    }
)


@dataclass(frozen=True)
class ClassificationResult:
    classification: DataClassification
    source: str
    reasons: tuple[str, ...]
    pii_categories: tuple[str, ...]


def _rank(classification: DataClassification) -> int:
    return _ORDER.index(classification)


def _escalate(
    current: DataClassification, floor: DataClassification
) -> DataClassification:
    return current if _rank(current) >= _rank(floor) else floor


def _normalize_source(source: str | None) -> str:
    return (source or "").strip().lower()


def _is_public_source(source_norm: str) -> bool:
    if not source_norm:
        return False
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", source_norm) if tok]
    return any(tok in PUBLIC_SOURCE_ALLOWLIST for tok in tokens)


def classify_content(
    source: str | None,
    text_sample: str | None,
    metadata: Mapping[str, Any] | None = None,
    *,
    audit_sink: Any | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    tenant_id: str | None = None,
) -> ClassificationResult:
    """Classify ``text_sample`` declared as coming from ``source``.

    Rules (monotonic — escalate only, never downgrade):
      * Allowlisted public source -> PUBLIC; otherwise default INTERNAL.
      * Any KSA-PII detected -> escalate to at least INTERNAL.
      * ``metadata["classification_floor"]`` (e.g. ``"RESTRICTED"``)
        escalates to at least that tier.

    When ``audit_sink`` plus ``trace_id``/``span_id``/``tenant_id`` are all
    supplied, a ``classification_decision`` record is appended to the
    sealed audit chain. Only PII category names are recorded.
    """
    source_norm = _normalize_source(source)
    reasons: list[str] = []

    if _is_public_source(source_norm):
        classification = DataClassification.PUBLIC
        reasons.append("allowlisted_public_source")
    else:
        classification = DataClassification.INTERNAL
        reasons.append("unrecognized_source_default_internal")

    pii_hits = detect_ksa_pii(text_sample or "")
    pii_categories = tuple(sorted({hit.category for hit in pii_hits}))
    if pii_hits:
        classification = _escalate(classification, DataClassification.INTERNAL)
        reasons.append("ksa_pii_detected")

    floor_raw = (metadata or {}).get("classification_floor")
    if isinstance(floor_raw, str):
        try:
            floor = DataClassification(floor_raw.strip().upper())
        except ValueError:
            pass
        else:
            classification = _escalate(classification, floor)
            reasons.append(f"metadata_floor:{floor.value}")

    result = ClassificationResult(
        classification=classification,
        source=source or "",
        reasons=tuple(reasons),
        pii_categories=pii_categories,
    )

    if audit_sink is not None and trace_id and span_id and tenant_id:
        audit_sink.append(
            event="classification_decision",
            trace_id=trace_id,
            span_id=span_id,
            tenant_id=tenant_id,
            payload={
                "source": result.source,
                "classification": result.classification.value,
                "pii_categories": list(result.pii_categories),
                "reasons": list(result.reasons),
            },
        )

    return result


__all__ = [
    "DataClassification",
    "ClassificationResult",
    "PUBLIC_SOURCE_ALLOWLIST",
    "classify_content",
]
