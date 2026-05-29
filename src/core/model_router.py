"""Sovereign local-only model router for Qarar.

The router never references or falls back to commercial providers. Public and
internal content may use either local Ollama or local llama.cpp; confidential
and restricted content are constrained to local llama.cpp only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, Field

from src.core.classification import DataClassification
from src.core.provider_interface import LLMProvider, ProviderError
from src.providers.local_llama_cpp import LocalLlamaCppProvider
from src.providers.local_ollama import LocalOllamaProvider

LOCAL_OLLAMA = "local_ollama"
LOCAL_LLAMA_CPP = "local_llama_cpp"

RouteStatus = Literal["COMPLETED", "BLOCKED"]
BlockedReason = Literal["BLOCKED_LOCAL_PROVIDER_UNAVAILABLE"]


class RouteDecision(BaseModel):
    """Typed route result returned by the sovereign model router."""

    status: RouteStatus
    classification: DataClassification
    provider_selected: str | None = None
    response: str | None = None
    route_reason: str
    blocked_reason: BlockedReason | None = None


class ProviderFailure(BaseModel):
    """Sanitized provider failure detail retained for audit payloads."""

    provider_name: str = Field(min_length=1)
    code: str = Field(min_length=1)


ProviderMap = Mapping[str, LLMProvider]


def default_local_providers() -> dict[str, LLMProvider]:
    """Build default local provider adapters.

    Returns:
        Mapping of local provider identifiers to concrete adapters.
    """

    ollama = LocalOllamaProvider()
    llama_cpp = LocalLlamaCppProvider()
    return {
        ollama.provider_name(): ollama,
        llama_cpp.provider_name(): llama_cpp,
    }


def normalize_classification(
    classification: DataClassification | str,
) -> DataClassification:
    """Normalize a caller-supplied classification value.

    Args:
        classification: Enum value or string classification label.

    Returns:
        ``DataClassification`` value.

    Raises:
        ValueError: If the classification is not one of Qarar's supported
            labels.
    """

    if isinstance(classification, DataClassification):
        return classification
    return DataClassification(classification.upper())


def provider_order_for_classification(
    classification: DataClassification | str,
) -> tuple[str, ...]:
    """Return the allowed local provider order for a classification.

    Args:
        classification: Qarar data classification.

    Returns:
        Ordered local provider identifiers. No external providers are ever
        returned by this function.
    """

    normalized = normalize_classification(classification)
    if normalized in {DataClassification.PUBLIC, DataClassification.INTERNAL}:
        return (LOCAL_OLLAMA, LOCAL_LLAMA_CPP)
    return (LOCAL_LLAMA_CPP,)


def _blocked_decision(
    classification: DataClassification,
    failures: Sequence[ProviderFailure],
) -> RouteDecision:
    provider_names = ", ".join(f.provider_name for f in failures) or "none"
    return RouteDecision(
        status="BLOCKED",
        classification=classification,
        provider_selected=None,
        response=None,
        route_reason=(
            "تم حظر التوجيه لأن جميع مزودي الاستدلال المحليين المسموحين "
            f"غير متاحين: {provider_names}."
        ),
        blocked_reason="BLOCKED_LOCAL_PROVIDER_UNAVAILABLE",
    )


async def route(
    classification: DataClassification | str,
    prompt: str,
    *,
    max_tokens: int = 512,
    providers: ProviderMap | None = None,
) -> RouteDecision:
    """Route and execute a prompt against allowed sovereign local providers.

    Args:
        classification: Data classification controlling provider eligibility.
        prompt: Prompt to send to the local model runtime.
        max_tokens: Maximum generated tokens.
        providers: Optional injected provider map for tests/runtime assembly.

    Returns:
        A completed or blocked ``RouteDecision``. Provider failures fail closed
        with ``BLOCKED_LOCAL_PROVIDER_UNAVAILABLE`` once no allowed local
        provider remains healthy.
    """

    normalized = normalize_classification(classification)
    provider_map = providers if providers is not None else default_local_providers()
    failures: list[ProviderFailure] = []

    for provider_name in provider_order_for_classification(normalized):
        provider = provider_map.get(provider_name)
        if provider is None:
            failures.append(ProviderFailure(provider_name=provider_name, code="PROVIDER_MISSING"))
            continue
        try:
            healthy = await provider.health()
            if not healthy:
                failures.append(
                    ProviderFailure(
                        provider_name=provider.provider_name(),
                        code="PROVIDER_UNAVAILABLE",
                    )
                )
                continue
            output = await provider.generate(prompt, max_tokens)
        except ProviderError as exc:
            failures.append(
                ProviderFailure(provider_name=exc.provider_name, code=exc.code)
            )
            continue
        except Exception:
            failures.append(
                ProviderFailure(
                    provider_name=provider.provider_name(),
                    code="PROVIDER_REQUEST_FAILED",
                )
            )
            continue

        return RouteDecision(
            status="COMPLETED",
            classification=normalized,
            provider_selected=provider.provider_name(),
            response=output,
            route_reason=(
                "تم اختيار مزود استدلال محلي مسموح وفق تصنيف البيانات "
                f"{normalized.value}."
            ),
        )

    return _blocked_decision(normalized, failures)
