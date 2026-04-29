"""Anthropic provider adapter boundary."""

from __future__ import annotations

import os

from .types import ProviderRequest, ProviderResponse


class AnthropicProvider:
    name = "anthropic"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured; Anthropic route is unavailable.")
        if os.environ.get("ALLOW_EXTERNAL_AI", "").lower() != "true":
            raise RuntimeError("ALLOW_EXTERNAL_AI=true is required before using Anthropic route.")
        raise NotImplementedError(
            "Anthropic transport is intentionally not implemented in the operations repo. "
            "Implement it in the product application boundary with explicit network authorization."
        )
