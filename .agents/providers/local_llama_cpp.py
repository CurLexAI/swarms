# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Local llama.cpp provider adapter (sovereign, offline-first).

Talks to a locally-running llama.cpp server over its OpenAI-compatible
HTTP API (``/v1/chat/completions``). The base URL is read from the
``LLAMACPP_BASE_URL`` environment variable and defaults to
``http://localhost:8080`` — a loopback host, so no traffic leaves the
sovereign boundary (Q8 egress allowlist; see
``.agents/policies/qala-egress-residency.md``). The default deliberately
uses ``localhost`` rather than ``127.0.0.1`` so the egress residency gate
stays green (static IP literals fail that gate).

No external AI APIs. No persistent state. No background workers. Conforms
to the synchronous ``Provider`` protocol in ``.types`` (``name`` +
``execute``); ``health`` is an additional best-effort liveness probe.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping

from .types import ProviderRequest, ProviderResponse

_DEFAULT_BASE_URL = "http://localhost:8080"
_COMPLETION_TIMEOUT_SECONDS = 120
_HEALTH_TIMEOUT_SECONDS = 5


def _base_url() -> str:
    return os.environ.get("LLAMACPP_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _build_prompt(task: str, metadata: Mapping[str, Any]) -> str:
    code = metadata.get("code", "")
    if code:
        return f"{task}\n\n{code}"
    return task


def _extract_content(body: Mapping[str, Any]) -> str:
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("Local llama.cpp returned no choices.")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise RuntimeError("Local llama.cpp returned an unexpected choice shape.")
    content = message.get("content", "")
    return content if isinstance(content, str) else ""


def _post_json(url: str, payload: Mapping[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Local llama.cpp request failed.") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Local llama.cpp returned a non-JSON response.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Local llama.cpp returned an unexpected payload shape.")
    return parsed


class LocalLlamaCppProvider:
    name = "local_llama_cpp"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        metadata = request.metadata or {}
        payload = {
            "model": request.model,
            "messages": [
                {"role": "user", "content": _build_prompt(request.task, metadata)}
            ],
            "stream": False,
        }
        body = _post_json(
            f"{_base_url()}/v1/chat/completions",
            payload,
            _COMPLETION_TIMEOUT_SECONDS,
        )
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            output=_extract_content(body),
            metadata={"base_url_env": "LLAMACPP_BASE_URL"},
        )

    def health(self) -> bool:
        """Best-effort liveness probe. True iff the server answers 2xx."""
        req = urllib.request.Request(f"{_base_url()}/health", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=_HEALTH_TIMEOUT_SECONDS) as response:
                return 200 <= int(response.status) < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False


__all__ = ["LocalLlamaCppProvider"]
