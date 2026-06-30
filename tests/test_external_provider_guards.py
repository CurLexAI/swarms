# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Fail-closed guard tests for the external / disabled provider adapters.

These adapters (`.agents/providers/anthropic_provider.py`,
`openai_provider.py`, `modal_provider.py`) are the sovereignty boundary that
keeps repository governance work offline-first: they must refuse to do
anything unless an operator has *deliberately* opted in via environment
flags, and the Modal adapter must stay disabled by policy outright.

This directly defends prohibition #4 ("do not call external AI APIs during
repository work unless explicitly authorized"): if a refactor ever weakened
the `ALLOW_EXTERNAL_AI` / API-key gate, these tests fail.

Contracts under test:

1. Anthropic / OpenAI raise ``RuntimeError`` when their API key is absent —
   before any network consideration.
2. With a key present but ``ALLOW_EXTERNAL_AI`` unset (or not exactly
   ``"true"``), they still raise ``RuntimeError`` — the deliberate-opt-in
   gate.
3. With both the key and ``ALLOW_EXTERNAL_AI=true``, they reach the
   intentionally-unimplemented transport and raise ``NotImplementedError``
   (proving the guards are ordered key -> flag -> transport, and that the
   repo ships no live external transport).
4. The Modal provider is disabled by policy and raises ``RuntimeError``
   unconditionally, regardless of environment.

No network I/O is performed; the adapters never get past their guards.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import TestCase, main, mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _ensure_pkg, _load_module, AGENTS_DIR  # noqa: E402

_PROVIDERS_DIR = AGENTS_DIR / "providers"
_ensure_pkg("_agents_pkg.providers", _PROVIDERS_DIR)
_load_module("_agents_pkg.providers.types", _PROVIDERS_DIR / "types.py")
provider_types = sys.modules["_agents_pkg.providers.types"]
anthropic_provider = _load_module(
    "_agents_pkg.providers.anthropic_provider",
    _PROVIDERS_DIR / "anthropic_provider.py",
)
openai_provider = _load_module(
    "_agents_pkg.providers.openai_provider",
    _PROVIDERS_DIR / "openai_provider.py",
)
modal_provider = _load_module(
    "_agents_pkg.providers.modal_provider",
    _PROVIDERS_DIR / "modal_provider.py",
)

ProviderRequest = provider_types.ProviderRequest
AnthropicProvider = anthropic_provider.AnthropicProvider
OpenAIProvider = openai_provider.OpenAIProvider
ModalProvider = modal_provider.ModalProvider


def _request() -> object:
    return ProviderRequest(task="explain", model="any-model")


def _env(**overrides: str) -> dict[str, str]:
    """A clean environment containing only the keys explicitly provided.

    ``clear=True`` on the patch wipes the inherited environment for the
    duration of the test so an ``ALLOW_EXTERNAL_AI`` (or API key) leaking
    in from the host shell cannot mask a broken guard.
    """

    return dict(overrides)


# At runtime the mixin inherits ``object`` so unittest does not collect it as a
# standalone test case (it has no ``provider_factory``); for type-checking it is
# a ``TestCase`` so the assertion helpers resolve. Concrete subclasses below mix
# in ``TestCase`` for real.
if TYPE_CHECKING:
    _MixinBase = TestCase
else:
    _MixinBase = object


class _ExternalProviderGuardMixin(_MixinBase):
    provider_factory: type[Any]
    api_key_env: str
    route_name: str

    def test_missing_api_key_raises_runtime_error(self) -> None:
        with mock.patch.dict("os.environ", _env(), clear=True):
            with self.assertRaisesRegex(RuntimeError, "not configured"):
                self.provider_factory().execute(_request())

    def test_key_present_but_external_ai_disabled_raises(self) -> None:
        with mock.patch.dict(
            "os.environ", _env(**{self.api_key_env: "sk-test"}), clear=True
        ):
            with self.assertRaisesRegex(RuntimeError, "ALLOW_EXTERNAL_AI"):
                self.provider_factory().execute(_request())

    def test_external_ai_flag_must_be_exactly_true(self) -> None:
        # A truthy-looking but non-"true" value must NOT open the gate.
        # Assert the specific gate message rather than bare RuntimeError:
        # NotImplementedError subclasses RuntimeError, so a loose assertion
        # would also accept the fall-through transport error and silently
        # pass even if a regression let one of these values open the gate.
        for sneaky in ("1", "yes", "TRUE ", "on", "enabled"):
            with self.subTest(value=sneaky):
                with mock.patch.dict(
                    "os.environ",
                    _env(**{self.api_key_env: "sk-test", "ALLOW_EXTERNAL_AI": sneaky}),
                    clear=True,
                ):
                    with self.assertRaisesRegex(RuntimeError, "ALLOW_EXTERNAL_AI"):
                        self.provider_factory().execute(_request())

    def test_fully_opted_in_reaches_unimplemented_transport(self) -> None:
        with mock.patch.dict(
            "os.environ",
            _env(**{self.api_key_env: "sk-test", "ALLOW_EXTERNAL_AI": "true"}),
            clear=True,
        ):
            with self.assertRaises(NotImplementedError):
                self.provider_factory().execute(_request())

    def test_true_is_case_insensitive(self) -> None:
        # The adapter lower-cases the flag, so "True"/"TRUE" must also open
        # the gate (and then hit the unimplemented transport).
        with mock.patch.dict(
            "os.environ",
            _env(**{self.api_key_env: "sk-test", "ALLOW_EXTERNAL_AI": "True"}),
            clear=True,
        ):
            with self.assertRaises(NotImplementedError):
                self.provider_factory().execute(_request())


class AnthropicProviderGuardTests(_ExternalProviderGuardMixin, TestCase):
    provider_factory = AnthropicProvider
    api_key_env = "ANTHROPIC_API_KEY"
    route_name = "anthropic"

    def test_name(self) -> None:
        self.assertEqual(AnthropicProvider().name, "anthropic")


class OpenAIProviderGuardTests(_ExternalProviderGuardMixin, TestCase):
    provider_factory = OpenAIProvider
    api_key_env = "OPENAI_API_KEY"
    route_name = "openai"

    def test_name(self) -> None:
        self.assertEqual(OpenAIProvider().name, "openai")


class ModalProviderGuardTests(TestCase):
    def test_name(self) -> None:
        self.assertEqual(ModalProvider().name, "modal_vllm")

    def test_disabled_by_policy_unconditionally(self) -> None:
        # No env combination may re-enable the Modal vLLM provider here:
        # Modal is backend-only and is not reachable from this routing path.
        for env in (
            _env(),
            _env(ALLOW_EXTERNAL_AI="true"),
            _env(MODAL_TOKEN_ID="x", MODAL_TOKEN_SECRET="y"),
        ):
            with self.subTest(env=sorted(env)):
                with mock.patch.dict("os.environ", env, clear=True):
                    with self.assertRaisesRegex(RuntimeError, "SECURITY_POLICY"):
                        ModalProvider().execute(_request())


if __name__ == "__main__":
    main()
