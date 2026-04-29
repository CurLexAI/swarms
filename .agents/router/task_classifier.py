"""Deterministic task classifier for Qarar routing."""

from __future__ import annotations

import re

from .types import TaskKind, TaskProfile


_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_CODE_HINTS = (
    "code",
    "typescript",
    "python",
    "refactor",
    "bug",
    "test",
    "build",
    "runtime",
    "deploy",
    "function",
    "class",
    "api",
)
_LEGAL_HINTS = (
    "legal",
    "law",
    "regulation",
    "pdpl",
    "sama",
    "nca",
    "compliance",
    "contract",
    "court",
    "statute",
    "نظام",
    "قانون",
    "لائحة",
    "امتثال",
    "ساما",
    "البيانات الشخصية",
)
_AGENT_HINTS = (
    "agent",
    "router",
    "orchestrator",
    "workflow",
    "swarm",
    "mihwar",
    "bayyinah",
    "وكيل",
    "وكلاء",
    "محور",
    "بينة",
)
_MULTIMODAL_HINTS = ("image", "screenshot", "pdf", "diagram", "audio", "video", "صورة", "مخطط")
_CRITICAL_HINTS = (
    "production",
    "security",
    "secret",
    "tenant",
    "payment",
    "auth",
    "admin",
    "regulatory",
    "high risk",
    "إنتاج",
    "أمني",
    "صلاحيات",
    "تنظيمي",
)


def _match_hints(hints: tuple[str, ...], text: str) -> bool:
    """Return True if any hint matches as a whole word in text."""
    for hint in hints:
        if _ARABIC_RE.search(hint):
            if hint in text:
                return True
        else:
            pattern = r"\b" + re.escape(hint) + r"\b"
            if re.search(pattern, text):
                return True
    return False


def classify_task(task: str, tenant_id: str | None = None) -> TaskProfile:
    normalized = task.lower()
    has_arabic = bool(_ARABIC_RE.search(task))
    is_code = _match_hints(_CODE_HINTS, normalized)
    is_legal = _match_hints(_LEGAL_HINTS, normalized)
    is_agent = _match_hints(_AGENT_HINTS, normalized)
    is_multimodal = _match_hints(_MULTIMODAL_HINTS, normalized)
    is_review = bool(re.search(r"\breview\b", normalized)) or "راجع" in task or "تدقيق" in task
    is_critical = _match_hints(_CRITICAL_HINTS, normalized)
    estimated_context_tokens = max(256, len(task.split()) * 2)

    if is_legal and (has_arabic or "saudi" in normalized or bool(re.search(r"\bsama\b", normalized))):
        kind = TaskKind.LEGAL_ANALYSIS
    elif is_review and is_code:
        kind = TaskKind.CODE_REVIEW
    elif is_agent:
        kind = TaskKind.AGENT_CREATION
    elif is_code:
        kind = TaskKind.CODING
    elif is_multimodal:
        kind = TaskKind.MULTIMODAL
    elif estimated_context_tokens > 12000 or "long context" in normalized:
        kind = TaskKind.LONG_CONTEXT_ANALYSIS
    elif is_critical:
        kind = TaskKind.CRITICAL_DECISION
    else:
        kind = TaskKind.FAST_DRAFT

    if is_critical or kind in {TaskKind.LEGAL_ANALYSIS, TaskKind.CRITICAL_DECISION}:
        risk = "critical"
    elif kind in {TaskKind.CODING, TaskKind.CODE_REVIEW, TaskKind.AGENT_CREATION}:
        risk = "high"
    elif is_multimodal:
        risk = "medium"
    else:
        risk = "low"

    return TaskProfile(
        kind=kind,
        risk=risk,
        requires_long_context=estimated_context_tokens > 12000 or kind == TaskKind.LONG_CONTEXT_ANALYSIS,
        requires_arabic_legal_precision=kind == TaskKind.LEGAL_ANALYSIS and has_arabic,
        requires_code_execution=kind in {TaskKind.CODING, TaskKind.CODE_REVIEW, TaskKind.AGENT_CREATION},
        requires_multimodal=is_multimodal,
        estimated_context_tokens=estimated_context_tokens,
        requires_citations=kind in {TaskKind.LEGAL_ANALYSIS, TaskKind.LONG_CONTEXT_ANALYSIS, TaskKind.CRITICAL_DECISION},
        tenant_id=tenant_id,
    )
