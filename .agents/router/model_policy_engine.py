# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Policy engine for selecting model routes.

This module intentionally avoids network calls. It maps a TaskProfile to a
route and makes reviewer requirements explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from .types import ModelRoute, ProviderKind, TaskKind, TaskProfile


class DataClassification(str, Enum):
    """Sovereign data-classification ladder for provider selection.

    Ordered from least to most restricted. SOVEREIGN covers KSA-regulated
    material (PDPL personal data, SAMA/NCA-scoped records) that must never
    leave sovereign-controlled runtimes.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SOVEREIGN = "sovereign"


# Claim-language alias (QAR-PAT-003 names the enum DATA_CLASSIFICATION).
DATA_CLASSIFICATION = DataClassification

# Providers that can never be selected, for any classification. These are
# hosted inference paths with no KSA data-residency or tenancy contract
# (see .agents/policies/qala-egress-residency.md). "huggingface" was
# removed from ProviderKind for the same reason; listing it here keeps the
# block permanent even if a caller passes it as a free-form candidate.
PERMANENTLY_BLOCKED_PROVIDERS: Final[frozenset[str]] = frozenset(
    {
        "huggingface",
        "openrouter",
        "community_proxy",
    }
)

# Allowlist per classification, most-restricted first. Sovereign-first:
# local runtimes always lead; external providers appear only where the
# classification permits egress.
_SOVEREIGN_PROVIDERS: Final[tuple[str, ...]] = (
    "local_ollama",
    "local_llama_cpp",
    "modal_vllm",
)
_CLASSIFICATION_ALLOWLIST: Final[dict[DataClassification, tuple[str, ...]]] = {
    DataClassification.SOVEREIGN: _SOVEREIGN_PROVIDERS,
    DataClassification.CONFIDENTIAL: _SOVEREIGN_PROVIDERS,
    DataClassification.INTERNAL: _SOVEREIGN_PROVIDERS + ("anthropic",),
    DataClassification.PUBLIC: _SOVEREIGN_PROVIDERS + ("anthropic", "openai"),
}


@dataclass(frozen=True)
class ProviderSelection:
    classification: DataClassification
    provider: ProviderKind
    allowed: tuple[str, ...]
    blocked: tuple[str, ...]
    reason: str


def select_provider_by_classification(
    classification: DataClassification | str,
    *,
    candidates: tuple[str, ...] | None = None,
) -> ProviderSelection:
    """Select the highest-priority provider permitted for a classification.

    Fail-closed: an unknown classification raises; a candidate list that
    leaves no permitted provider raises. Providers in
    ``PERMANENTLY_BLOCKED_PROVIDERS`` are excluded unconditionally — no
    classification, candidate list, or caller flag can re-enable them.
    """
    resolved = DataClassification(classification)
    allowlist = _CLASSIFICATION_ALLOWLIST[resolved]

    pool = allowlist if candidates is None else tuple(
        p for p in allowlist if p in candidates
    )
    blocked = tuple(
        p
        for p in (candidates or allowlist)
        if p in PERMANENTLY_BLOCKED_PROVIDERS or p not in allowlist
    )
    permitted = tuple(p for p in pool if p not in PERMANENTLY_BLOCKED_PROVIDERS)

    if not permitted:
        raise ValueError(
            f"No permitted provider for classification {resolved.value!r} "
            f"with candidates {candidates!r}. Sovereign routing fails closed."
        )

    return ProviderSelection(
        classification=resolved,
        provider=permitted[0],  # type: ignore[arg-type]
        allowed=permitted,
        blocked=blocked,
        reason=(
            f"classification={resolved.value}: sovereign-first order "
            f"{permitted}; permanently blocked providers are never eligible."
        ),
    )


# Claim-language alias (QAR-PAT-003 names selectProviderByClassification()).
selectProviderByClassification = select_provider_by_classification


def choose_route(profile: TaskProfile) -> ModelRoute:
    if profile.risk == "critical" or profile.requires_arabic_legal_precision:
        return ModelRoute(
            provider="anthropic",
            model="claude-opus-or-sonnet-current",
            reason="High-risk or Arabic legal reasoning requires long-context analytical routing plus Bayyinah validation.",
            requires_reviewer=True,
            reviewer_agent_id="bayyinah",
        )

    if profile.requires_multimodal:
        return ModelRoute(
            provider="openai",
            model="gpt-current",
            reason="Multimodal input requires OpenAI multimodal-capable path regardless of task kind.",
            requires_reviewer=profile.risk != "low",
            reviewer_agent_id="bayyinah" if profile.risk != "low" else None,
        )

    if profile.kind in {TaskKind.CODING, TaskKind.CODE_REVIEW, TaskKind.AGENT_CREATION}:
        return ModelRoute(
            provider="local_ollama",
            model="mihwar" if profile.kind != TaskKind.CODE_REVIEW else "bayyinah",
            reason="Sovereign coding path uses local Ollama agents with Bayyinah validation for sensitive output.",
            requires_reviewer=profile.kind != TaskKind.CODE_REVIEW,
            reviewer_agent_id="bayyinah" if profile.kind != TaskKind.CODE_REVIEW else None,
        )

    if profile.kind == TaskKind.FAST_DRAFT:
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

    raise ValueError(
        f"No route defined for task kind {profile.kind!r} with risk {profile.risk!r}. "
        "Add an explicit handler for this combination in choose_route."
    )
