# Licensed under MIT
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lex-node"))

import verify_registry  # noqa: E402


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data: dict[str, Any] = json.loads(
            (ROOT / "config" / "lex-sovereign-node-registry.example.json").read_text()
        )

    def test_example_is_valid(self) -> None:
        self.assertTrue(verify_registry.verify(self.data))

    def test_rejects_shared_keys(self) -> None:
        self.data["heartbeat"]["key_env"] = self.data["attestation"]["key_env"]
        with self.assertRaises(ValueError):
            verify_registry.verify(self.data)

    def test_rejects_bad_ttl(self) -> None:
        self.data["heartbeat"]["ttl_seconds"] = 901
        with self.assertRaises(ValueError):
            verify_registry.verify(self.data)

    def test_attestation_requires_key(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(self.data, f)
            path = f.name
        try:
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "lex-node" / "attest.py"),
                    "--registry",
                    path,
                ],
                capture_output=True,
                text=True,
                env={},
            )
            self.assertNotEqual(run.returncode, 0)
        finally:
            os.unlink(path)

    def test_heartbeat_is_signed(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(self.data, f)
            path = f.name
        try:
            env = {"LEX_NODE_HEARTBEAT_KEY": "test-only-key"}
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "lex-node" / "heartbeat.py"),
                    "--registry",
                    path,
                ],
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            value = json.loads(run.stdout)
            self.assertEqual(value["algorithm"], "HMAC-SHA256")
            self.assertEqual(value["payload"]["node_id"], self.data["node_id"])
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
