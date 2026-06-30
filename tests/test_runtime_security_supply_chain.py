# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Supply-chain guard tests for `.agents/runtime_security.py`.

`require_pinned_revision` and `trust_remote_code_for` are the fail-closed
helpers that refuse to load a model from a mutable ref, or to execute remote
model code, unless BOTH a pinned 40-char commit SHA AND a deliberate
acknowledgement are present. They run inside the GPU model-loading path and
are the last line of defence against accidental supply-chain code execution
from a mutable Hugging Face ref.

The existing token-contract suite exercises `verify_bearer_token` and
`require_qdrant_auth`; these two helpers had no direct coverage. This module
closes that gap.

`runtime_security` is dependency-light (stdlib only on this path; `fastapi`
is imported lazily inside `verify_bearer_token`), so it loads as a standalone
module without the `.agents` package shim.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest import TestCase, main, mock

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_runtime_security() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "runtime_security", REPO_ROOT / ".agents" / "runtime_security.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so the frozen dataclass can resolve its own
    # ``__module__`` during class processing.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rs = _load_runtime_security()

# A real-shaped lowercase 40-hex commit SHA.
_VALID_SHA = "0123456789abcdef0123456789abcdef01234567"


class RequirePinnedRevisionTests(TestCase):
    ENV = "MIHWAR_MODEL_REVISION"

    def test_missing_revision_raises(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, f"{self.ENV}_missing"):
                rs.require_pinned_revision(self.ENV)

    def test_empty_or_whitespace_revision_raises_missing(self) -> None:
        for value in ("", "   ", "\t\n"):
            with self.subTest(value=repr(value)):
                with mock.patch.dict("os.environ", {self.ENV: value}, clear=True):
                    with self.assertRaisesRegex(RuntimeError, f"{self.ENV}_missing"):
                        rs.require_pinned_revision(self.ENV)

    def test_mutable_ref_is_rejected(self) -> None:
        # Branch names, tags, and short SHAs are mutable / ambiguous refs and
        # must be refused — this is the core supply-chain protection.
        for mutable in ("main", "v1.0", "latest", "abc1234", _VALID_SHA[:39]):
            with self.subTest(ref=mutable):
                with mock.patch.dict("os.environ", {self.ENV: mutable}, clear=True):
                    with self.assertRaisesRegex(
                        RuntimeError, f"{self.ENV}_must_be_full_40_char_commit_sha"
                    ):
                        rs.require_pinned_revision(self.ENV)

    def test_uppercase_hex_is_rejected(self) -> None:
        # The matcher is lowercase-only; an uppercase SHA must not pass.
        with mock.patch.dict("os.environ", {self.ENV: _VALID_SHA.upper()}, clear=True):
            with self.assertRaises(RuntimeError):
                rs.require_pinned_revision(self.ENV)

    def test_too_long_is_rejected(self) -> None:
        with mock.patch.dict("os.environ", {self.ENV: _VALID_SHA + "0"}, clear=True):
            with self.assertRaises(RuntimeError):
                rs.require_pinned_revision(self.ENV)

    def test_valid_pinned_sha_is_returned(self) -> None:
        with mock.patch.dict("os.environ", {self.ENV: _VALID_SHA}, clear=True):
            self.assertEqual(rs.require_pinned_revision(self.ENV), _VALID_SHA)

    def test_surrounding_whitespace_is_trimmed(self) -> None:
        with mock.patch.dict(
            "os.environ", {self.ENV: f"  {_VALID_SHA}\n"}, clear=True
        ):
            self.assertEqual(rs.require_pinned_revision(self.ENV), _VALID_SHA)


class TrustRemoteCodeForTests(TestCase):
    REVISION_ENV = "BAYYINAH_MODEL_REVISION"
    ACK_ENV = "BAYYINAH_REMOTE_CODE_ACK"

    def _policy(self) -> object:
        return rs.ModelPolicy(
            model_id="Qwen/Qwen2.5-Coder-32B-Instruct",
            revision_env=self.REVISION_ENV,
            remote_code_ack_env=self.ACK_ENV,
        )

    def test_unpinned_revision_raises_before_consulting_ack(self) -> None:
        # Even with a perfect acknowledgement, an unpinned revision must fail
        # closed: the SHA check runs first.
        with mock.patch.dict(
            "os.environ", {self.ACK_ENV: rs.REMOTE_CODE_ACK}, clear=True
        ):
            with self.assertRaises(RuntimeError):
                rs.trust_remote_code_for(self._policy())

    def test_pinned_without_ack_returns_false(self) -> None:
        with mock.patch.dict(
            "os.environ", {self.REVISION_ENV: _VALID_SHA}, clear=True
        ):
            self.assertFalse(rs.trust_remote_code_for(self._policy()))

    def test_pinned_with_wrong_ack_value_returns_false(self) -> None:
        for wrong in ("true", "1", "yes", rs.REMOTE_CODE_ACK.lower(), "ALLOW"):
            with self.subTest(ack=wrong):
                with mock.patch.dict(
                    "os.environ",
                    {self.REVISION_ENV: _VALID_SHA, self.ACK_ENV: wrong},
                    clear=True,
                ):
                    self.assertFalse(rs.trust_remote_code_for(self._policy()))

    def test_pinned_with_exact_ack_returns_true(self) -> None:
        with mock.patch.dict(
            "os.environ",
            {self.REVISION_ENV: _VALID_SHA, self.ACK_ENV: rs.REMOTE_CODE_ACK},
            clear=True,
        ):
            self.assertTrue(rs.trust_remote_code_for(self._policy()))

    def test_ack_constant_is_the_documented_sentinel(self) -> None:
        # Lock the sentinel value: operators set this exact string out-of-band.
        self.assertEqual(rs.REMOTE_CODE_ACK, "ALLOW_PINNED_REVIEWED_REMOTE_CODE")


if __name__ == "__main__":
    main()
