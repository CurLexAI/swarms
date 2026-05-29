"""Local Ollama adapter for sovereign inference."""

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


class OllamaGeneratePayload(BaseModel):
    """Ollama ``/api/generate`` request payload."""

    model: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    stream: bool = False
    options: dict[str, int]


class OllamaGenerateResult(BaseModel):
    """Subset of the Ollama generate response required by Qarar."""

    response: str = ""
    done: bool = True


class LocalOllamaProvider(LLMProvider):
    """Concrete local-only Ollama provider adapter.

    Args:
        base_url: Optional local/internal Ollama URL. Defaults to the
            ``OLLAMA_BASE_URL`` environment variable or ``http://ollama:11434``.
        model: Optional model name. Defaults to ``OLLAMA_MODEL`` or a local
            Qwen coder model identifier.
        timeout_seconds: Request timeout for local HTTP calls.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        provider = self.provider_name()
        configured_url = base_url or read_env_url("OLLAMA_BASE_URL", "http://ollama:11434")
        self._base_url = require_sovereign_local_url(configured_url, provider)
        self._model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:32b")
        self._timeout_seconds = timeout_seconds

    def provider_name(self) -> str:
        """Return the router provider key for Ollama."""

        return "local_ollama"

    async def health(self) -> bool:
        """Check local Ollama health using its tags endpoint."""

        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=5.0) as client:
                response = await client.get("/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text through the local Ollama API."""

        request = ProviderGenerateRequest(prompt=prompt, max_tokens=max_tokens)
        payload = OllamaGeneratePayload(
            model=self._model,
            prompt=request.prompt,
            stream=False,
            options={"num_predict": request.max_tokens},
        )
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.post("/api/generate", json=payload.model_dump())
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(
                "PROVIDER_REQUEST_FAILED",
                self.provider_name(),
                "تعذر تنفيذ طلب الاستدلال عبر Ollama المحلي.",
            ) from exc

        body: dict[str, Any] = response.json()
        parsed = OllamaGenerateResult.model_validate(body)
        return parsed.response
