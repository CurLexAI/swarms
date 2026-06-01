# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
Integration test: pr_review.py ↔ Modal endpoint HTTP relay.

Mocks `requests.post` (used by `_call_endpoint` and `_post_comment` in
`.agents/pr_review.py`) to assert the contract pr_review.py honours when
talking to the deployed Modal web endpoints for Bayyinah and Mihwar.

Covers:
1. Successful Bayyinah review path posts a formatted GitHub comment.
2. Endpoint 5xx errors are sanitized: raw upstream text never reaches
   the GitHub comment body.
3. Network errors are sanitized — the secret endpoint URL is not leaked.
4. Missing `BAYYINAH_ENDPOINT` / `AGENT_API_TOKEN` causes a clean exit(1)
   with no HTTP call attempted.

Run:
    python -m unittest tests.pr_review.modal_relay.integration.test
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import requests  # type: ignore[import-untyped]


REPO_ROOT = Path(__file__).resolve().parent.parent
PR_REVIEW_PATH = REPO_ROOT / ".agents" / "pr_review.py"


def _load_pr_review() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("pr_review", PR_REVIEW_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pr_review = _load_pr_review()


def _make_args(agent: str = "bayyinah", bayyinah_report: str = "") -> argparse.Namespace:
    return argparse.Namespace(
        diff="/tmp/unused.diff",
        pr=42,
        repo="CurLexAI/swarms",
        head_sha="abc1234567890def",
        agent=agent,
        bayyinah_report=bayyinah_report,
    )


def _fake_response(status: int, payload: Any) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    if isinstance(payload, (dict, list)):
        resp.json.return_value = payload
        resp.text = json.dumps(payload)
    else:
        resp.text = str(payload)
        resp.json.side_effect = ValueError("not json")
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(
            f"{status} error", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class BayyinahRelayContractTests(unittest.TestCase):
    """Bayyinah Modal endpoint payload + comment posting contract."""

    def setUp(self) -> None:
        self.env_patch = patch.dict(
            "os.environ",
            {
                "BAYYINAH_ENDPOINT": "https://bayyinah.modal.example/api",
                "AGENT_API_TOKEN": "secret-token-xyz",
                "GITHUB_TOKEN": "test-github-token",
            },
            clear=False,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_approve_verdict_returns_cleanly(self) -> None:
        endpoint_response = _fake_response(
            200,
            {
                "verdict": "APPROVE",
                "report": "Clean.",
                "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
            },
        )
        comment_response = _fake_response(201, {"html_url": "https://github.com/x/y/issues/42#c"})

        with patch.object(pr_review.requests, "post", side_effect=[endpoint_response, comment_response]) as mock_post:
            args = _make_args(agent="bayyinah")
            with patch.object(pr_review, "_load_diff", return_value="diff text"), \
                 patch.object(pr_review, "_parse_args", return_value=args), \
                 patch.object(pr_review, "_set_output"):
                pr_review.main()  # should not raise SystemExit on APPROVE

        # First call is the Modal endpoint
        endpoint_call = mock_post.call_args_list[0]
        self.assertEqual(endpoint_call.args[0], "https://bayyinah.modal.example/api")
        sent_payload = endpoint_call.kwargs["json"]
        # Token must be in Authorization header, NOT in the JSON body
        self.assertNotIn("token", sent_payload)
        sent_headers = endpoint_call.kwargs["headers"]
        self.assertEqual(sent_headers.get("Authorization"), "Bearer secret-token-xyz")
        self.assertIn("code", sent_payload)
        self.assertIn("PR #42 in CurLexAI/swarms", sent_payload["context"])

        # Second call is the GitHub comment
        comment_call = mock_post.call_args_list[1]
        self.assertIn("api.github.com/repos/CurLexAI/swarms/issues/42/comments",
                      comment_call.args[0])
        body = comment_call.kwargs["json"]["body"]
        self.assertIn("Bayyinah Code Review", body)
        self.assertIn("APPROVED", body)

    def test_request_changes_verdict_exits_nonzero(self) -> None:
        endpoint_response = _fake_response(
            200,
            {
                "verdict": "REQUEST_CHANGES",
                "report": "[CRITICAL] file.py:1 — leak",
                "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
            },
        )
        comment_response = _fake_response(201, {"html_url": "https://x"})

        with patch.object(pr_review.requests, "post", side_effect=[endpoint_response, comment_response]):
            args = _make_args(agent="bayyinah")
            with patch.object(pr_review, "_load_diff", return_value="diff text"), \
                 patch.object(pr_review, "_parse_args", return_value=args), \
                 patch.object(pr_review, "_set_output"):
                with self.assertRaises(SystemExit) as ctx:
                    pr_review.main()
                self.assertEqual(ctx.exception.code, 1,
                                 "REQUEST_CHANGES must mark the check as failed")


class ErrorSanitizationTests(unittest.TestCase):
    """Endpoint URL and upstream errors must never leak through _call_endpoint."""

    def test_network_error_omits_endpoint_url(self) -> None:
        secret_url = "https://very-secret-endpoint.modal.run/abc-token-xyz"
        with patch.object(pr_review.requests, "post",
                          side_effect=requests.ConnectionError(f"refused at {secret_url}")):
            result = pr_review._call_endpoint(secret_url, {"token": "t"})
        self.assertIn("error", result)
        self.assertNotIn(secret_url, result["error"],
                         "secret endpoint URL must not appear in error message")
        self.assertNotIn("abc-token-xyz", result["error"])

    def test_timeout_returns_clean_message(self) -> None:
        with patch.object(pr_review.requests, "post", side_effect=requests.Timeout()):
            result = pr_review._call_endpoint("https://x.modal.run", {"token": "t"})
        self.assertEqual(result, {"error": "Agent timed out after 300s"})

    def test_5xx_response_returns_error_dict(self) -> None:
        bad_response = _fake_response(503, "stack trace with secret=hunter2")
        with patch.object(pr_review.requests, "post", return_value=bad_response):
            result = pr_review._call_endpoint("https://x.modal.run", {"token": "t"})
        self.assertIn("error", result)
        self.assertNotIn("hunter2", result["error"],
                         "raw upstream body must not be embedded in returned error")


class MissingSecretsTests(unittest.TestCase):
    """_require_env must hard-fail before any HTTP call when secrets are missing."""

    def test_missing_bayyinah_endpoint_exits_before_http(self) -> None:
        with patch.dict("os.environ", {"BAYYINAH_ENDPOINT": "", "AGENT_API_TOKEN": "t"}, clear=False):
            with patch.object(pr_review.requests, "post") as mock_post:
                with self.assertRaises(SystemExit) as ctx:
                    pr_review._run_bayyinah("diff", _make_args(agent="bayyinah"))
                self.assertEqual(ctx.exception.code, 1)
            mock_post.assert_not_called()

    def test_missing_mihwar_endpoint_exits_before_http(self) -> None:
        with patch.dict("os.environ", {"MIHWAR_ENDPOINT": "", "AGENT_API_TOKEN": "t"}, clear=False):
            with patch.object(pr_review.requests, "post") as mock_post:
                with self.assertRaises(SystemExit) as ctx:
                    pr_review._run_mihwar("diff", _make_args(agent="mihwar"))
                self.assertEqual(ctx.exception.code, 1)
            mock_post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
