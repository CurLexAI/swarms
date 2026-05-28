# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/providers/local_ollama.py` and
`.agents/providers/local_llama_cpp.py`.

Contracts under test:

1. Both providers conform to the synchronous Provider protocol
   (`name` + `execute(ProviderRequest) -> ProviderResponse`).
2. `execute` POSTs to the configured loopback base URL and unwraps the
   provider-specific response shape into `ProviderResponse.output`.
3. `health()` returns True on a 2xx answer and False when the server is
   unreachable — it never raises.
4. The base URL is environment-configurable.

All HTTP is mocked; no network calls are made.
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _ensure_pkg, _load_module, AGENTS_DIR  # noqa: E402

_PROVIDERS_DIR = AGENTS_DIR / "providers"
_ensure_pkg("_agents_pkg.providers", _PROVIDERS_DIR)
_load_module("_agents_pkg.providers.types", _PROVIDERS_DIR / "types.py")
provider_types = sys.modules["_agents_pkg.providers.types"]
local_ollama = _load_module(
    "_agents_pkg.providers.local_ollama", _PROVIDERS_DIR / "local_ollama.py"
)
local_llama_cpp = _load_module(
    "_agents_pkg.providers.local_llama_cpp", _PROVIDERS_DIR / "local_llama_cpp.py"
)

ProviderRequest = provider_types.ProviderRequest
ProviderResponse = provider_types.ProviderResponse
LocalOllamaProvider = local_ollama.LocalOllamaProvider
LocalLlamaCppProvider = local_llama_cpp.LocalLlamaCppProvider


class _FakeResponse:
    def __init__(self, body: str, status: int = 200) -> None:
        self._body = body.encode("utf-8")
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _request(model: str = "test-model", **metadata: object) -> object:
    return ProviderRequest(task="explain", model=model, metadata=dict(metadata) or None)


class LocalOllamaProviderTests(unittest.TestCase):
    def test_conforms_to_provider_protocol(self):
        provider = LocalOllamaProvider()
        self.assertEqual(provider.name, "local_ollama")
        self.assertTrue(callable(provider.execute))

    def test_execute_unwraps_response_field(self):
        provider = LocalOllamaProvider()
        body = json.dumps({"response": "hello world", "done": True})
        with mock.patch.object(
            urllib.request, "urlopen", return_value=_FakeResponse(body)
        ):
            result = provider.execute(_request(code="print(1)"))
        self.assertIsInstance(result, ProviderResponse)
        self.assertEqual(result.provider, "local_ollama")
        self.assertEqual(result.model, "test-model")
        self.assertEqual(result.output, "hello world")
        self.assertEqual(result.metadata["base_url_env"], "OLLAMA_BASE_URL")

    def test_execute_raises_clean_error_on_transport_failure(self):
        provider = LocalOllamaProvider()
        with mock.patch.object(
            urllib.request, "urlopen", side_effect=urllib.error.URLError("boom")
        ):
            with self.assertRaises(RuntimeError):
                provider.execute(_request())

    def test_health_true_on_2xx(self):
        provider = LocalOllamaProvider()
        with mock.patch.object(
            urllib.request, "urlopen", return_value=_FakeResponse("{}", status=200)
        ):
            self.assertTrue(provider.health())

    def test_health_false_when_unreachable(self):
        provider = LocalOllamaProvider()
        with mock.patch.object(
            urllib.request, "urlopen", side_effect=urllib.error.URLError("down")
        ):
            self.assertFalse(provider.health())

    def test_base_url_is_env_configurable(self):
        with mock.patch.dict(
            "os.environ", {"OLLAMA_BASE_URL": "http://localhost:9999/"}, clear=False
        ):
            self.assertEqual(local_ollama._base_url(), "http://localhost:9999")


class LocalLlamaCppProviderTests(unittest.TestCase):
    def test_conforms_to_provider_protocol(self):
        provider = LocalLlamaCppProvider()
        self.assertEqual(provider.name, "local_llama_cpp")
        self.assertTrue(callable(provider.execute))

    def test_execute_unwraps_openai_chat_shape(self):
        provider = LocalLlamaCppProvider()
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
        )
        with mock.patch.object(
            urllib.request, "urlopen", return_value=_FakeResponse(body)
        ):
            result = provider.execute(_request())
        self.assertEqual(result.provider, "local_llama_cpp")
        self.assertEqual(result.output, "done")

    def test_execute_raises_on_empty_choices(self):
        provider = LocalLlamaCppProvider()
        body = json.dumps({"choices": []})
        with mock.patch.object(
            urllib.request, "urlopen", return_value=_FakeResponse(body)
        ):
            with self.assertRaises(RuntimeError):
                provider.execute(_request())

    def test_health_true_on_2xx(self):
        provider = LocalLlamaCppProvider()
        with mock.patch.object(
            urllib.request, "urlopen", return_value=_FakeResponse("{}", status=204)
        ):
            self.assertTrue(provider.health())

    def test_health_false_when_unreachable(self):
        provider = LocalLlamaCppProvider()
        with mock.patch.object(
            urllib.request, "urlopen", side_effect=OSError("refused")
        ):
            self.assertFalse(provider.health())


if __name__ == "__main__":
    unittest.main()
