# SPDX-License-Identifier: MIT
# Licensed under MIT
"""OpenAI provider adapter.

The adapter is intentionally disabled unless explicitly configured by env. This
keeps repository maintenance offline-first and prevents accidental data egress.
"""

from __future__ import annotations

import os

from .types import ProviderRequest, ProviderResponse


class OpenAIProvider:
    name = "openai"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if os.environ.get("ALLOW_EXTERNAL_AI", "").lower() != "true":
            raise RuntimeError("ALLOW_EXTERNAL_AI=true is required before using OpenAI route.")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured; OpenAI route is unavailable.")
        raise NotImplementedError(
            "OpenAI transport is intentionally not implemented in the operations repo. "
            "Implement it in the product application boundary, not in repository governance code."
        )
