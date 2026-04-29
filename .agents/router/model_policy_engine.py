"""Policy engine for selecting model routes.

This module intentionally avoids network calls. It maps a TaskProfile to a
route and makes reviewer requirements explicit.
"""

from __future__ import annotations

from .types import ModelRoute, TaskKind, TaskProfile


def choose_route(profile: TaskProfile) -> ModelRoute:
    if profile.risk == "critical" or profile.requires_arabic_legal_precision:
        return ModelRoute(
            provider="anthropic",
            model="claude-opus-or-sonnet-current",
            reason="High-risk or Arabic legal reasoning requires long-context analytical routing plus Bayyinah validation.",
            requires_reviewer=True,
            reviewer_agent_id="bayyinah",
        )

    if profile.kind in {TaskKind.CODING, TaskKind.CODE_REVIEW, TaskKind.AGENT_CREATION}:
        return ModelRoute(
            provider="modal_vllm",
            model="mihwar" if profile.kind != TaskKind.CODE_REVIEW else "bayyinah",
            reason="Sovereign coding path uses Modal/vLLM agents with Bayyinah validation for sensitive output.",
            requires_reviewer=profile.kind != TaskKind.CODE_REVIEW,
            reviewer_agent_id="bayyinah" if profile.kind != TaskKind.CODE_REVIEW else None,
        )

    if profile.requires_multimodal or profile.kind == TaskKind.FAST_DRAFT:
        return ModelRoute(
            provider="openai",
            model="gpt-current",
            reason="Fast multimodal or draft-heavy task benefits from OpenAI tool and multimodal path.",
            requires_reviewer=profile.risk != "low",
            reviewer_agent_id="bayyinah" if profile.risk != "low" else None,
        )

    if profile.kind == TaskKind.LONG_CONTEXT_ANALYSIS:
        return ModelRoute(
            provider="anthropic",
            model="claude-sonnet-current",
            reason="Long-context analysis requires a dedicated long-context reasoning path.",
            requires_reviewer=True,
            reviewer_agent_id="bayyinah",
        )

    return ModelRoute(
        provider="openai",
        model="gpt-current-mini",
        reason="Low-risk default path.",
        requires_reviewer=False,
        reviewer_agent_id=None,
    )
