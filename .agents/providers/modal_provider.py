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
        raise RuntimeError(
            "SECURITY_POLICY: modal_vllm provider is disabled. "
            "Use local_ollama or local_llama_cpp instead. "
            "Ref: models.config.json#providers.modal_vllm.status"
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
