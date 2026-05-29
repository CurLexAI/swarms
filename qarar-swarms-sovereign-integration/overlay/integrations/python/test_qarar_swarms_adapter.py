# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from qarar_swarms.adapter import DataContext, QararSovereignToolClient, QararToolRequest


class QararSwarmsAdapterTests(unittest.TestCase):
    def test_data_context_blocks_public_pii(self) -> None:
        context = DataContext(trace_id="trace-1", data_class="PUBLIC", contains_pii=True)
        with self.assertRaises(ValueError):
            context.to_api()

    def test_request_rejects_model_task_mismatch(self) -> None:
        request = QararToolRequest(
            prompt="hello",
            task_type="LEGAL_REASONING",
            agent_id="agent-1",
            model_id="allam-7b",
            data_context=DataContext(trace_id="trace-2"),
        )
        with self.assertRaises(ValueError):
            request.to_api()

    @patch("qarar_swarms.adapter.requests.post")
    def test_client_posts_without_leaking_token(self, post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "text": "ok",
            "confidence": 0.9,
            "protocol": "ACP",
            "escalated": False,
            "sources": [],
        }
        post.return_value = response

        client = QararSovereignToolClient(
            base_url="https://qarar.internal/",
            token="secret-token",
            timeout_seconds=1,
        )
        result = client.complete(
            QararToolRequest(
                prompt="hello",
                task_type="LEGAL_REASONING",
                agent_id="agent-1",
                model_id="deepseek-r1-32b",
                data_context=DataContext(trace_id="trace-3"),
            )
        )

        self.assertEqual(result.text, "ok")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://qarar.internal/api/sovereign/swarms/complete")
        self.assertEqual(kwargs["headers"]["authorization"], "Bearer secret-token")


if __name__ == "__main__":
    unittest.main()
