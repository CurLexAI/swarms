# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Lock the gateway stub's no-proxy property.

These tests are the contract for `.agents/gateway/mcp_server.py` while
ADR-0005 is undecided:
- The module must refuse to start without explicit operator ack.
- It must not import or reference Modal client code.
- Every model-routing endpoint must return HTTP 501.
- No private endpoint URL or auth token must appear in the source.

If ADR-0005 is rejected, delete `.agents/gateway/` and this file.
If ADR-0005 is accepted, do NOT relax these tests in the same PR;
authenticate the change against the ADR-0006 design first.
"""

from __future__ import annotations

import importlib
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATEWAY_DIR = ROOT / ".agents" / "gateway"
MODULE_PATH = GATEWAY_DIR / "mcp_server.py"


class GatewayStubContract(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(MODULE_PATH.exists(), "stub module missing")
        # Make sure each test gets a fresh import so the start-time guard
        # runs against the current environment.
        for name in list(sys.modules):
            if name == "mcp_server" or name.startswith("mcp_server."):
                del sys.modules[name]
        sys.path.insert(0, str(GATEWAY_DIR))
        self.addCleanup(lambda: sys.path.remove(str(GATEWAY_DIR)))
        self._prev_ack = os.environ.pop("SWARMS_GATEWAY_STUB_ACK", None)

    def tearDown(self) -> None:
        if self._prev_ack is None:
            os.environ.pop("SWARMS_GATEWAY_STUB_ACK", None)
        else:
            os.environ["SWARMS_GATEWAY_STUB_ACK"] = self._prev_ack

    def test_refuses_to_start_without_ack(self) -> None:
        try:
            import fastapi  # noqa: F401
        except ImportError:
            self.skipTest("fastapi not installed in this environment")
        module = importlib.import_module("mcp_server")
        self.assertIsNone(
            module.app,
            "stub must not start without SWARMS_GATEWAY_STUB_ACK",
        )

    def test_source_does_not_reference_modal(self) -> None:
        src = MODULE_PATH.read_text(encoding="utf-8")
        lowered = src.lower()
        forbidden = ["modal.run", "modal_app", "agent_api_token",
                     "bayyinah_endpoint", "mihwar_endpoint"]
        for token in forbidden:
            self.assertNotIn(
                token, lowered,
                f"stub source must not reference {token!r}",
            )

    def test_source_has_no_real_endpoint_url(self) -> None:
        src = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            "agents.lexprim.com", src,
            "stub must not hardcode a production gateway hostname",
        )
        self.assertNotIn(
            "https://", src,
            "stub must not embed any outbound HTTPS URL",
        )

    def test_all_model_routes_return_501(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("fastapi/starlette not installed")
        os.environ["SWARMS_GATEWAY_STUB_ACK"] = "1"
        module = importlib.import_module("mcp_server")
        app = module.create_app()
        client = TestClient(app)
        for method, path in [
            ("post", "/v1/chat/completions"),
            ("post", "/v1/completions"),
            ("get", "/v1/models"),
        ]:
            if method == "post":
                resp = client.post(path, json={})
            else:
                resp = client.get(path)
            self.assertEqual(
                resp.status_code, 501,
                f"{method.upper()} {path} must return 501 until ADR-0005",
            )
            body = resp.json()
            self.assertIn("ADR-0005", body.get("error", ""))


if __name__ == "__main__":
    unittest.main()
