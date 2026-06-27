# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/providers/huggingface_provider.py`.

All HTTP is mocked; no live Hugging Face request is made.
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.request
from pathlib import Path
from typing import Any, cast
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _ensure_pkg, _load_module, AGENTS_DIR  # noqa: E402

_PROVIDERS_DIR = AGENTS_DIR / "providers"
_ensure_pkg("_agents_pkg.providers", _PROVIDERS_DIR)
_load_module("_agents_pkg.providers.types", _PROVIDERS_DIR / "types.py")
provider_types = sys.modules["_agents_pkg.providers.types"]
huggingface_provider = _load_module(
    "_agents_pkg.providers.huggingface_provider",
    _PROVIDERS_DIR / "huggingface_provider.py",
)

ProviderRequest = provider_types.ProviderRequest
HuggingFaceProvider = huggingface_provider.HuggingFaceProvider


class _FakeResponse:
    status = 200

    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _completion(content: str = "done") -> str:
    return json.dumps({"choices": [{"message": {"content": content}}]})


class HuggingFaceProviderTests(unittest.TestCase):
    def test_disabled_by_default_without_network(self) -> None:
        provider = HuggingFaceProvider()
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch.object(
            urllib.request, "urlopen"
        ) as urlopen:
            with self.assertRaisesRegex(RuntimeError, "HF_INTEGRATION_MODE"):
                provider.execute(ProviderRequest(task="write code", model="mihwar"))
        urlopen.assert_not_called()

    def test_requires_hf_token_when_enabled(self) -> None:
        provider = HuggingFaceProvider()
        with mock.patch.dict(
            "os.environ", {"HF_INTEGRATION_MODE": "inference_providers"}, clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "HF_TOKEN"):
                provider.execute(ProviderRequest(task="review code", model="bayyinah"))

    def test_mihwar_uses_deepseek_default_and_sanitized_metadata(self) -> None:
        provider = HuggingFaceProvider()
        captured: dict[str, object] = {}

        def fake_urlopen(req: urllib.request.Request, timeout: int) -> _FakeResponse:
            captured["url"] = req.full_url
            captured["timeout"] = timeout
            captured["auth"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[union-attr]
            return _FakeResponse(_completion("mihwar-ok"))

        env = {
            "HF_INTEGRATION_MODE": "inference_providers",
            "HF_TOKEN": "hf_test_token",
        }
        with mock.patch.dict("os.environ", env, clear=True), mock.patch.object(
            urllib.request, "urlopen", side_effect=fake_urlopen
        ):
            result = provider.execute(
                ProviderRequest(
                    task="Implement a parser",
                    model="mihwar",
                    metadata={"code": "print(1)"},
                )
            )

        self.assertEqual(captured["url"], "https://router.huggingface.co/v1/chat/completions")
        self.assertEqual(captured["auth"], "Bearer hf_test_token")
        self.assertIsInstance(captured["body"], dict)
        body = cast(dict[str, Any], captured["body"])
        self.assertEqual(body["model"], "deepseek-ai/DeepSeek-Coder-V2-Instruct")
        self.assertEqual(result.provider, "huggingface")
        self.assertEqual(result.model, "mihwar")
        self.assertEqual(result.output, "mihwar-ok")
        self.assertEqual(result.metadata["token_env"], "HF_TOKEN")
        self.assertNotIn("hf_test_token", json.dumps(result.metadata))

    def test_bayyinah_supports_provider_suffix(self) -> None:
        provider = HuggingFaceProvider()
        captured: dict[str, object] = {}

        def fake_urlopen(req: urllib.request.Request, timeout: int) -> _FakeResponse:
            captured["body"] = json.loads(req.data.decode("utf-8"))  # type: ignore[union-attr]
            return _FakeResponse(_completion("bayyinah-ok"))

        env = {
            "HF_INTEGRATION_MODE": "inference_providers",
            "HF_TOKEN": "hf_test_token",
            "BAYYINAH_HF_PROVIDER": "together",
        }
        with mock.patch.dict("os.environ", env, clear=True), mock.patch.object(
            urllib.request, "urlopen", side_effect=fake_urlopen
        ):
            result = provider.execute(ProviderRequest(task="Review this", model="bayyinah"))

        self.assertIsInstance(captured["body"], dict)
        body = cast(dict[str, Any], captured["body"])
        self.assertEqual(body["model"], "Qwen/Qwen2.5-Coder-32B-Instruct:together")
        self.assertEqual(result.output, "bayyinah-ok")

    def test_rejects_non_router_base_url(self) -> None:
        provider = HuggingFaceProvider()
        env = {
            "HF_INTEGRATION_MODE": "inference_providers",
            "HF_TOKEN": "hf_test_token",
            "HF_INFERENCE_BASE_URL": "https://evil.example.invalid/v1",
        }
        with mock.patch.dict("os.environ", env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "router.huggingface.co"):
                provider.execute(ProviderRequest(task="x", model="mihwar"))


if __name__ == "__main__":
    unittest.main()
