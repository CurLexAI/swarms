# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Provider adapter package.

Each provider conforms to the synchronous ``Provider`` protocol in
``types`` (``name`` + ``execute``). Local providers are offline-first and
loopback-only; remote providers stay backend-only and are gated by their
own environment flags.
"""

from .anthropic_provider import AnthropicProvider
from .local_llama_cpp import LocalLlamaCppProvider
from .local_ollama import LocalOllamaProvider
from .modal_provider import ModalProvider
from .openai_provider import OpenAIProvider
from .types import Provider, ProviderRequest, ProviderResponse

__all__ = [
    "Provider",
    "ProviderRequest",
    "ProviderResponse",
    "ModalProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "LocalOllamaProvider",
    "LocalLlamaCppProvider",
]
