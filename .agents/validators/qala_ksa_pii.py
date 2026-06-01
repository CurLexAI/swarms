# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Qal'a (قلعة) — Q5 Sovereign KSA-PII Detector (Python side).

Detects Saudi-specific identifiers in text payloads. Distinct from
generic secret detection in ``sovereignCyberRadar.SECRET_PATTERNS`` and
adapter ``SENSITIVE_PATTERNS``.

Raw match values are NEVER returned. Each hit is reported as
``KsaPiiHit(category, masked_value, span)`` where ``masked_value``
preserves only the first/last two characters with the middle replaced
by ``…``. Callers may pass results to the Q7 audit sink without
re-redaction.

No network calls. No persistent state. No background workers.

Mirror of ``src/security/qalaKsaPii.ts``. See
``docs/decisions/ADR-0003-qala-security-architecture.md`` §Q5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

KsaPiiCategory = Literal[
    "KSA_NATIONAL_ID",
    "KSA_IQAMA",
    "KSA_IBAN",
    "KSA_MOBILE",
    "KSA_COMMERCIAL_REGISTRATION",
    "KSA_ID_AMBIGUOUS_10DIGIT",
]


@dataclass(frozen=True)
class KsaPiiHit:
    category: KsaPiiCategory
    masked_value: str
    span: tuple[int, int]


# ── Patterns ────────────────────────────────────────────────────────────────
#
# Word-boundary discipline matters: 10-digit shapes (National ID, Iqama, CR)
# overlap heavily, so we anchor with (?<!\d) and (?!\d) to avoid matching
# substrings of longer digit runs. Leading-digit discrimination follows:
#   National ID  : leading 1
#   Iqama        : leading 2
#   CR           : leading 7 (common KSA CR prefix); ambiguous 10-digit
#                  shapes outside {1,2,7} are reported as KSA_ID_AMBIGUOUS_10DIGIT.

_IBAN_RE: Final[re.Pattern[str]] = re.compile(r"\bSA\d{22}\b")
_NATIONAL_ID_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)1\d{9}(?!\d)")
_IQAMA_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)2\d{9}(?!\d)")
_CR_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)7\d{9}(?!\d)")
_AMBIGUOUS_10DIGIT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<!\d)[3-689]\d{9}(?!\d)"
)
# Saudi mobile: +9665XXXXXXXX | 9665XXXXXXXX | 05XXXXXXXX (10 digits with leading 0)
_MOBILE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<!\d)(?:\+?966\s?5\d{8}|05\d{8})(?!\d)"
)


def _mask(value: str) -> str:
    """Preserve first/last two chars; replace middle with ``…``.

    Examples:
        "1234567890"     -> "12…90"
        "SA0000000000…"  -> "SA…<last2>"
        "05XXXXXXXX"     -> "05…<last2>"
    For inputs shorter than 4 chars, returns ``"…"`` to avoid leaking
    any character at all.
    """
    if len(value) < 4:
        return "…"
    return f"{value[:2]}…{value[-2:]}"


def _scan(
    pattern: re.Pattern[str],
    text: str,
    category: KsaPiiCategory,
) -> list[KsaPiiHit]:
    return [
        KsaPiiHit(category=category, masked_value=_mask(m.group(0)), span=m.span())
        for m in pattern.finditer(text)
    ]


def detect_ksa_pii(text: str) -> tuple[KsaPiiHit, ...]:
    """Return all detected KSA-PII hits, deduplicated by span.

    Categories are anti-collision: IBAN matches do not double-count as
    10-digit IDs, and 10-digit IDs are partitioned by leading digit
    into National ID / Iqama / CR / Ambiguous.
    """
    if not isinstance(text, str) or len(text) == 0:
        return ()

    hits: list[KsaPiiHit] = []
    consumed: set[tuple[int, int]] = set()

    # IBAN first — it's the most specific shape and would otherwise
    # be mis-classified as a number inside an alphanumeric blob.
    for hit in _scan(_IBAN_RE, text, "KSA_IBAN"):
        if hit.span not in consumed:
            hits.append(hit)
            consumed.add(hit.span)

    # Mobile next — its anchoring includes country-code shapes that
    # do not overlap with the 10-digit ID anchors.
    for hit in _scan(_MOBILE_RE, text, "KSA_MOBILE"):
        if hit.span not in consumed:
            hits.append(hit)
            consumed.add(hit.span)

    # 10-digit IDs partitioned by leading digit.
    for pattern, category in (
        (_NATIONAL_ID_RE, "KSA_NATIONAL_ID"),
        (_IQAMA_RE, "KSA_IQAMA"),
        (_CR_RE, "KSA_COMMERCIAL_REGISTRATION"),
        (_AMBIGUOUS_10DIGIT_RE, "KSA_ID_AMBIGUOUS_10DIGIT"),
    ):
        for hit in _scan(pattern, text, category):  # type: ignore[arg-type]
            if hit.span not in consumed:
                hits.append(hit)
                consumed.add(hit.span)

    return tuple(sorted(hits, key=lambda h: h.span))


def has_ksa_pii(text: str) -> bool:
    return len(detect_ksa_pii(text)) > 0


def redact_ksa_pii(text: str) -> str:
    """Return ``text`` with every KSA-PII span replaced by its mask.

    Raw values never appear in the output.
    """
    hits = detect_ksa_pii(text)
    if not hits:
        return text
    pieces: list[str] = []
    cursor = 0
    for hit in hits:
        start, end = hit.span
        pieces.append(text[cursor:start])
        pieces.append(f"[{hit.category}:{hit.masked_value}]")
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


__all__ = [
    "KsaPiiCategory",
    "KsaPiiHit",
    "detect_ksa_pii",
    "has_ksa_pii",
    "redact_ksa_pii",
]
