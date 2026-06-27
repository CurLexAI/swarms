# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Modal/vLLM provider adapter for Mihwar and Bayyinah endpoints."""

from __future__ import annotations

from .types import ProviderRequest, ProviderResponse


class ModalProvider:
    name = "modal_vllm"

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        raise RuntimeError(
            "SECURITY_POLICY: modal_vllm provider is disabled. "
            "Use local_ollama or local_llama_cpp instead. "
            "Ref: models.config.json#providers.modal_vllm.status"
        )
