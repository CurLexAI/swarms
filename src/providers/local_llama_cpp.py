"""Local llama.cpp OpenAI-compatible adapter for sovereign inference."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from src.core.provider_interface import (
    LLMProvider,
    ProviderError,
    ProviderGenerateRequest,
    read_env_url,
    require_sovereign_local_url,
)


class LlamaCppMessage(BaseModel):
    """OpenAI-compatible chat message for llama.cpp."""

    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class LlamaCppChatPayload(BaseModel):
    """llama.cpp OpenAI-compatible chat-completions payload."""

    model: str = Field(min_length=1)
    messages: list[LlamaCppMessage]
    max_tokens: int = Field(ge=1, le=8192)
    stream: bool = False


class LlamaCppChoiceMessage(BaseModel):
    """OpenAI-compatible choice message returned by llama.cpp."""

    content: str = ""


class LlamaCppChoice(BaseModel):
    """OpenAI-compatible choice wrapper returned by llama.cpp."""

    message: LlamaCppChoiceMessage


class LlamaCppChatResult(BaseModel):
    """Subset of llama.cpp chat response required by Qarar."""

    choices: list[LlamaCppChoice]


class LocalLlamaCppProvider(LLMProvider):
    """Concrete local-only llama.cpp provider adapter.

    Args:
        base_url: Optional local/internal llama.cpp server URL. Defaults to the
            ``LLAMA_CPP_BASE_URL`` environment variable or
            ``http://llama-server:8080``.
        model: Optional model name, defaulting to ``LLAMA_CPP_MODEL``.
        timeout_seconds: Request timeout for local HTTP calls.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        provider = self.provider_name()
        configured_url = base_url or read_env_url(
            "LLAMA_CPP_BASE_URL",
            "http://llama-server:8080",
        )
        self._base_url = require_sovereign_local_url(configured_url, provider)
        self._model = model or os.environ.get("LLAMA_CPP_MODEL", "local-sovereign")
        self._timeout_seconds = timeout_seconds

    def provider_name(self) -> str:
        """Return the router provider key for llama.cpp."""

        return "local_llama_cpp"

    async def health(self) -> bool:
        """Check local llama.cpp health endpoint."""

        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=5.0) as client:
                response = await client.get("/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text through local llama.cpp OpenAI-compatible API."""

        request = ProviderGenerateRequest(prompt=prompt, max_tokens=max_tokens)
        payload = LlamaCppChatPayload(
            model=self._model,
            messages=[LlamaCppMessage(role="user", content=request.prompt)],
            max_tokens=request.max_tokens,
            stream=False,
        )
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.post(
                    "/v1/chat/completions",
                    json=payload.model_dump(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                "PROVIDER_REQUEST_FAILED",
                self.provider_name(),
                "تعذر تنفيذ طلب الاستدلال عبر llama.cpp المحلي.",
            ) from exc

        body: dict[str, Any] = response.json()
        parsed = LlamaCppChatResult.model_validate(body)
        if not parsed.choices:
            raise ProviderError(
                "PROVIDER_INVALID_RESPONSE",
                self.provider_name(),
                "استجابة llama.cpp المحلية لا تحتوي على نتيجة صالحة.",
            )
        return parsed.choices[0].message.content
