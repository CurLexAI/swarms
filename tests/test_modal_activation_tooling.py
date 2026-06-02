# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for the Modal runtime activation control-plane tooling.

These cover the scripts the **Modal Runtime Activation** workflow
(`.github/workflows/modal-runtime-activation.yml`) runs in its "Validation
gates" and "Endpoint smoke" steps:

- ``scripts/commander/agent-presence-gate.sh``
- ``scripts/commander/p0-security-test-gate.sh``
- ``scripts/commander/modal-runtime-smoke.sh``

Guarantees locked in here:

1. Missing Modal secrets yield a non-fatal HOLD / ``UNVERIFIED_SECRET_MISSING``
   verdict — never a false ``FAIL``. (Both gate scripts previously contained a
   botched-merge ``PYTHON_BIN`` fragment that crashed the Python interpreter and
   failed the activation job regardless of secrets.)
2. A successful endpoint smoke yields ``VERIFIED_ENDPOINT_SMOKE``.

No real secrets are used; the success path is exercised against a localhost
mock HTTP server.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDER = REPO_ROOT / "scripts" / "commander"
PRESENCE_GATE = COMMANDER / "agent-presence-gate.sh"
P0_GATE = COMMANDER / "p0-security-test-gate.sh"
SMOKE = COMMANDER / "modal-runtime-smoke.sh"

_SECRET_VARS = (
    "BAYYINAH_ENDPOINT",
    "MIHWAR_ENDPOINT",
    "BAYYINAH_API_TOKEN",
    "MIHWAR_API_TOKEN",
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
)


def _env_without_secrets() -> dict[str, str]:
    env = dict(os.environ)
    for name in _SECRET_VARS:
        env.pop(name, None)
    return env


def _run(cmd: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )


class _OkHandler(BaseHTTPRequestHandler):
    """Minimal handler that answers any POST with a 200 JSON body."""

    def do_POST(self) -> None:  # noqa: N802 - http.server dispatch name
        body = json.dumps({"ok": True}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Silence the default stderr access log during tests.
        return


class AgentPresenceGateTests(unittest.TestCase):
    def test_passes_without_secrets(self) -> None:
        result = _run(["bash", str(PRESENCE_GATE)], _env_without_secrets())
        detail = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, detail)
        self.assertIn("configured_agent_count=2", result.stdout)
        self.assertIn("SECRET_MISSING", result.stdout)
        self.assertNotIn("[FAIL]", result.stdout)


class P0SecurityGateTests(unittest.TestCase):
    def test_passes_without_secrets(self) -> None:
        result = _run(["bash", str(P0_GATE)], _env_without_secrets())
        detail = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, detail)
        self.assertNotIn("PYTHON_BIN=", detail)


class ModalSmokeTests(unittest.TestCase):
    def test_hold_without_secrets(self) -> None:
        result = _run(["bash", str(SMOKE)], _env_without_secrets())
        detail = result.stdout + result.stderr
        self.assertEqual(result.returncode, 2, detail)
        self.assertIn("STATUS=UNVERIFIED_SECRET_MISSING", result.stdout)

    def test_ready_with_mock_endpoints(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _OkHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = int(server.server_address[1])
            url = f"http://127.0.0.1:{port}/smoke"
            env = _env_without_secrets()
            env["BAYYINAH_ENDPOINT"] = url
            env["MIHWAR_ENDPOINT"] = url
            env["BAYYINAH_API_TOKEN"] = "test-bayyinah-token"  # noqa: S105 - dummy
            env["MIHWAR_API_TOKEN"] = "test-mihwar-token"  # noqa: S105 - dummy
            result = _run(["bash", str(SMOKE)], env)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        detail = result.stdout + result.stderr
        self.assertEqual(result.returncode, 0, detail)
        self.assertIn("STATUS=VERIFIED_ENDPOINT_SMOKE", result.stdout)


if __name__ == "__main__":
    unittest.main()
