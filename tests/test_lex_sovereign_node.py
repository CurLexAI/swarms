# Licensed under MIT
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lex-node"))

import verify_registry  # noqa: E402


@contextmanager
def _private_workspace() -> Iterator[Path]:
    """Chdir into a private directory so registry fixtures sit under cwd.

    The registry path confinement rejects the shared system temp tree
    (privileged-installer TOCTOU), so CLI fixtures must live below the
    invoking working directory instead.
    """
    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="lex-node-") as tmp:
        os.chdir(tmp)
        try:
            yield Path(tmp)
        finally:
            os.chdir(previous_cwd)


class RegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data: dict[str, Any] = json.loads(
            (ROOT / "config" / "lex-sovereign-node-registry.example.json").read_text()
        )

    def _write_registry(self, workspace: Path) -> Path:
        path = workspace / "registry.json"
        path.write_text(json.dumps(self.data), encoding="utf-8")
        return path

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

    def test_load_registry_accepts_working_directory_path(self) -> None:
        with _private_workspace() as workspace:
            path = self._write_registry(workspace)
            value = verify_registry.load_registry(path)
            self.assertEqual(value["node_id"], self.data["node_id"])

    def test_load_registry_rejects_path_outside_permitted_roots(self) -> None:
        with self.assertRaises(ValueError):
            verify_registry.load_registry("/nonexistent-root/registry.json")

    def test_load_registry_rejects_shared_temp_path(self) -> None:
        # The shared system temp tree is rejected even for a valid registry:
        # the privileged installer reopens the path as root after validation,
        # so a world-writable location would permit a swap in between.
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(self.data, f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                verify_registry.load_registry(path)
        finally:
            os.unlink(path)

    def test_confine_only_checks_path_without_reading_content(self) -> None:
        with _private_workspace() as workspace:
            # Not valid JSON — --confine-only must still pass because it
            # checks the path boundary only and never reads the file.
            path = workspace / "registry.json"
            path.write_text("not json at all", encoding="utf-8")
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "lex-node" / "verify_registry.py"),
                    "--confine-only",
                    str(path),
                ],
                capture_output=True,
                text=True,
                cwd=workspace,
            )
            self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)

    def test_confine_only_rejects_outside_path(self) -> None:
        with _private_workspace() as workspace:
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "lex-node" / "verify_registry.py"),
                    "--confine-only",
                    "/nonexistent-root/registry.json",
                ],
                capture_output=True,
                text=True,
                cwd=workspace,
            )
            self.assertEqual(run.returncode, 2)

    def test_attestation_requires_key(self) -> None:
        with _private_workspace() as workspace:
            path = self._write_registry(workspace)
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "lex-node" / "attest.py"),
                    "--registry",
                    str(path),
                ],
                capture_output=True,
                text=True,
                env={},
                cwd=workspace,
            )
            self.assertNotEqual(run.returncode, 0)

    def test_heartbeat_is_signed(self) -> None:
        with _private_workspace() as workspace:
            path = self._write_registry(workspace)
            env = {"LEX_NODE_HEARTBEAT_KEY": "test-only-key"}
            run = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "lex-node" / "heartbeat.py"),
                    "--registry",
                    str(path),
                ],
                capture_output=True,
                text=True,
                env=env,
                cwd=workspace,
                check=True,
            )
            value = json.loads(run.stdout)
            self.assertEqual(value["algorithm"], "HMAC-SHA256")
            self.assertEqual(value["payload"]["node_id"], self.data["node_id"])


if __name__ == "__main__":
    unittest.main()
