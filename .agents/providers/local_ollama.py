# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Local Ollama provider adapter (sovereign, offline-first).

Talks to a locally-running Ollama server over its HTTP API. The base URL
is read from the ``OLLAMA_BASE_URL`` environment variable and defaults to
``http://localhost:11434`` — a loopback host, so no traffic leaves the
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

_DEFAULT_BASE_URL = "http://localhost:11434"
_GENERATE_TIMEOUT_SECONDS = 120
_HEALTH_TIMEOUT_SECONDS = 5


def _base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _build_prompt(task: str, metadata: Mapping[str, Any]) -> str:
    code = metadata.get("code", "")
    if code:
        return f"{task}\n\n{code}"
    return task


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
        raise RuntimeError("Local Ollama request failed.") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Local Ollama returned a non-JSON response.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Local Ollama returned an unexpected payload shape.")
    return parsed


class LocalOllamaProvider:
    name = "local_ollama"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        metadata = request.metadata or {}
        payload = {
            "model": request.model,
            "prompt": _build_prompt(request.task, metadata),
            "stream": False,
        }
        body = _post_json(
            f"{_base_url()}/api/generate", payload, _GENERATE_TIMEOUT_SECONDS
        )
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            output=body.get("response", ""),
            metadata={
                "base_url_env": "OLLAMA_BASE_URL",
                "done": body.get("done"),
            },
        )

    def health(self) -> bool:
        """Best-effort liveness probe. True iff the server answers 2xx."""
        req = urllib.request.Request(f"{_base_url()}/api/tags", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=_HEALTH_TIMEOUT_SECONDS) as response:
                return 200 <= int(response.status) < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False


__all__ = ["LocalOllamaProvider"]
