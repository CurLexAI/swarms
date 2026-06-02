# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Modal/vLLM provider adapter for Mihwar and Bayyinah endpoints."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .types import ProviderRequest, ProviderResponse


class ModalProvider:
    name = "modal_vllm"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        endpoint = _endpoint_for_model(request.model)
        token_env = _token_env_for_model(request.model)
        token = os.environ.get(token_env, "")
        if not endpoint:
            raise RuntimeError(f"Modal endpoint is not configured for model {request.model!r}.")
        if not token:
            raise RuntimeError(f"{token_env} is not configured.")

        metadata = request.metadata or {}
        payload = {
            "task": request.task,
            "code": metadata.get("code", ""),
            "context": json.dumps(metadata, ensure_ascii=False),
            "context_files": {},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                body = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("Modal endpoint request failed without exposing endpoint details.") from exc

        return ProviderResponse(
            provider=self.name,
            model=request.model,
            output=json.loads(body),
            metadata={"endpoint_env": _endpoint_env_for_model(request.model)},
        )


def _endpoint_env_for_model(model: str) -> str:
    if model == "bayyinah":
        return "BAYYINAH_ENDPOINT"
    return "MIHWAR_ENDPOINT"


def _token_env_for_model(model: str) -> str:
    if model == "bayyinah":
        return "BAYYINAH_API_TOKEN"
    return "MIHWAR_API_TOKEN"


def _endpoint_for_model(model: str) -> str:
    return os.environ.get(_endpoint_env_for_model(model), "")
