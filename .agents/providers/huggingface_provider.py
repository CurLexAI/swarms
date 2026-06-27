# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Hugging Face Inference Providers adapter for Mihwar and Bayyinah.

This adapter is backend-only and disabled unless ``HF_INTEGRATION_MODE`` is set
to ``inference_providers``. It calls Hugging Face's OpenAI-compatible chat
completion router with ``HF_TOKEN`` from the secret store. No token value is ever
returned in metadata or error text.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.parse import urlparse
import urllib.error
import urllib.request

from .types import ProviderRequest, ProviderResponse

_DEFAULT_BASE_URL = "https://router.huggingface.co/v1"
_COMPLETION_TIMEOUT_SECONDS = 180
_ENABLED_MODE = "inference_providers"
_TOKEN_ENV = "HF_TOKEN"
_LEGACY_TOKEN_ENV = "HF_READ_TOKEN"

_MODEL_ENV_BY_AGENT = {
    "mihwar": "MIHWAR_HF_MODEL_ID",
    "bayyinah": "BAYYINAH_HF_MODEL_ID",
}
_DEFAULT_MODEL_BY_AGENT = {
    "mihwar": "deepseek-ai/DeepSeek-Coder-V2-Instruct",
    "bayyinah": "Qwen/Qwen2.5-Coder-32B-Instruct",
}
_PROVIDER_SUFFIX_ENV_BY_AGENT = {
    "mihwar": "MIHWAR_HF_PROVIDER",
    "bayyinah": "BAYYINAH_HF_PROVIDER",
}
_MAX_TOKENS_ENV_BY_AGENT = {
    "mihwar": "MIHWAR_HF_MAX_TOKENS",
    "bayyinah": "BAYYINAH_HF_MAX_TOKENS",
}
_DEFAULT_MAX_TOKENS_BY_AGENT = {
    "mihwar": 8192,
    "bayyinah": 4096,
}
_TEMPERATURE_ENV_BY_AGENT = {
    "mihwar": "MIHWAR_HF_TEMPERATURE",
    "bayyinah": "BAYYINAH_HF_TEMPERATURE",
}
_DEFAULT_TEMPERATURE_BY_AGENT = {
    "mihwar": 0.1,
    "bayyinah": 0.0,
}


def _integration_mode() -> str:
    return os.environ.get("HF_INTEGRATION_MODE", "disabled").strip().lower()


def _token() -> str:
    return os.environ.get(_TOKEN_ENV, "").strip() or os.environ.get(
        _LEGACY_TOKEN_ENV, ""
    ).strip()


def _base_url() -> str:
    base_url = os.environ.get("HF_INFERENCE_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https":
        raise RuntimeError("HF_INFERENCE_BASE_URL must use https.")
    if parsed.username or parsed.password:
        raise RuntimeError("HF_INFERENCE_BASE_URL must not contain credentials.")
    if parsed.hostname != "router.huggingface.co":
        raise RuntimeError("HF_INFERENCE_BASE_URL host must be router.huggingface.co.")
    return base_url


def _canonical_agent(model: str) -> str:
    return "bayyinah" if model == "bayyinah" else "mihwar"


def _model_id(agent: str) -> str:
    model_env = _MODEL_ENV_BY_AGENT[agent]
    model = os.environ.get(model_env, _DEFAULT_MODEL_BY_AGENT[agent]).strip()
    if not model:
        raise RuntimeError(f"{model_env} must be a non-empty Hugging Face model id.")

    provider_suffix = os.environ.get(_PROVIDER_SUFFIX_ENV_BY_AGENT[agent], "").strip()
    if provider_suffix and ":" not in model:
        return f"{model}:{provider_suffix}"
    return model


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero.")
    return value


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number.") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be zero or greater.")
    return value


def _build_prompt(task: str, metadata: Mapping[str, Any]) -> str:
    pieces = [task]
    code = metadata.get("code")
    if isinstance(code, str) and code.strip():
        pieces.append(code)
    context = metadata.get("context")
    if isinstance(context, str) and context.strip():
        pieces.append(context)
    context_files = metadata.get("context_files")
    if isinstance(context_files, Mapping) and context_files:
        pieces.append(json.dumps(context_files, ensure_ascii=False, sort_keys=True))
    return "\n\n".join(pieces)


def _messages(agent: str, task: str, metadata: Mapping[str, Any]) -> list[dict[str, str]]:
    if agent == "bayyinah":
        system = (
            "You are Bayyinah, a precise code review and validation agent. "
            "Return actionable findings with severity, file references when available, "
            "and a clear verdict."
        )
    else:
        system = (
            "You are Mihwar, a senior software architect and code generation agent. "
            "Return complete, runnable implementation guidance and call out assumptions."
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": _build_prompt(task, metadata)},
    ]


def _extract_content(body: Mapping[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Hugging Face returned no choices.")
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    if not isinstance(message, dict):
        raise RuntimeError("Hugging Face returned an unexpected choice shape.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Hugging Face returned an empty completion.")
    return content.strip()


def _post_chat_completion(payload: Mapping[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_base_url()}/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_COMPLETION_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Hugging Face request failed with HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Hugging Face request failed without exposing credentials.") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Hugging Face returned a non-JSON response.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Hugging Face returned an unexpected payload shape.")
    return parsed


class HuggingFaceProvider:
    name = "huggingface"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if _integration_mode() != _ENABLED_MODE:
            raise RuntimeError(
                "HF_INTEGRATION_MODE=inference_providers is required before using Hugging Face."
            )
        if not _token():
            raise RuntimeError("HF_TOKEN is not configured.")

        agent = _canonical_agent(request.model)
        metadata = request.metadata or {}
        model_id = _model_id(agent)
        payload = {
            "model": model_id,
            "messages": _messages(agent, request.task, metadata),
            "max_tokens": _int_env(
                _MAX_TOKENS_ENV_BY_AGENT[agent], _DEFAULT_MAX_TOKENS_BY_AGENT[agent]
            ),
            "temperature": _float_env(
                _TEMPERATURE_ENV_BY_AGENT[agent],
                _DEFAULT_TEMPERATURE_BY_AGENT[agent],
            ),
            "stream": False,
        }
        body = _post_chat_completion(payload)
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            output=_extract_content(body),
            metadata={
                "model_id": model_id,
                "base_url_env": "HF_INFERENCE_BASE_URL",
                "token_env": _TOKEN_ENV,
            },
        )


__all__ = ["HuggingFaceProvider"]
