"""Ports for sovereign local model providers.

The router depends on this abstract port instead of concrete HTTP adapters.
Concrete adapters live under ``src.providers`` and are injected into routing
functions for tests and runtime composition.
"""

from __future__ import annotations

import ipaddress
import os
from abc import ABC, abstractmethod
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field

ProviderErrorCode = Literal[
    "PROVIDER_BLOCKED_URL",
    "PROVIDER_INVALID_RESPONSE",
    "PROVIDER_REQUEST_FAILED",
    "PROVIDER_UNAVAILABLE",
]


class ProviderGenerateRequest(BaseModel):
    """Typed model-generation request accepted by local providers."""

    prompt: str = Field(min_length=1)
    max_tokens: int = Field(default=512, ge=1, le=8192)


class ProviderGenerateResponse(BaseModel):
    """Typed model-generation response returned by local providers."""

    provider_name: str = Field(min_length=1)
    text: str


class ProviderError(Exception):
    """Typed provider failure surfaced at routing boundaries.

    Args:
        code: Stable machine-readable failure code.
        provider_name: Provider that raised the failure.
        message: Human-readable operational message with no secrets.
    """

    def __init__(self, code: ProviderErrorCode, provider_name: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.provider_name = provider_name
        self.message = message


class LLMProvider(ABC):
    """Abstract port implemented by local-only LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate text from a local provider.

        Args:
            prompt: Prompt to send to the local model runtime.
            max_tokens: Maximum number of tokens to produce.

        Returns:
            Generated text.

        Raises:
            ProviderError: When the local provider is unavailable, rejects the
                request, or returns an invalid response.
        """

    @abstractmethod
    async def health(self) -> bool:
        """Return whether the local provider is healthy."""

    @abstractmethod
    def provider_name(self) -> str:
        """Return the stable provider identifier used by the router."""


_LOCAL_HOST_SUFFIXES = (".internal", ".local", ".svc", ".cluster.local")
_ALLOWED_LOCAL_HOSTS = frozenset(
    {
        "localhost",
        "ollama",
        "llama-server",
        "llama.cpp",
        "llamacpp",
        "127.0.0.1",
        "::1",
    }
)


def is_sovereign_local_url(base_url: str) -> bool:
    """Return whether a URL targets a local/internal model runtime.

    Args:
        base_url: Base URL configured for a local model provider.

    Returns:
        ``True`` only for loopback, RFC1918/private IPs, Docker service names,
        or explicitly internal DNS suffixes. Public hostnames are rejected.
    """

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if host is None or len(host) == 0:
        return False
    normalized_host = host.lower().strip("[]")
    if normalized_host in _ALLOWED_LOCAL_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(normalized_host)
    except ValueError:
        return normalized_host.endswith(_LOCAL_HOST_SUFFIXES)
    return ip.is_loopback or ip.is_private or ip.is_link_local


def require_sovereign_local_url(base_url: str, provider_name: str) -> str:
    """Validate that a provider URL cannot route to public infrastructure.

    Args:
        base_url: Candidate provider base URL.
        provider_name: Stable provider name for typed error reporting.

    Returns:
        The stripped URL when accepted.

    Raises:
        ProviderError: If the URL is public, malformed, or unsupported.
    """

    normalized_url = base_url.strip().rstrip("/")
    if not is_sovereign_local_url(normalized_url):
        raise ProviderError(
            "PROVIDER_BLOCKED_URL",
            provider_name,
            "تم حظر عنوان مزود النموذج لأنه ليس ضمن النطاق المحلي السيادي.",
        )
    return normalized_url


def read_env_url(name: str, default: str) -> str:
    """Read a provider URL from environment without exposing secret values."""

    return os.environ.get(name, default)
