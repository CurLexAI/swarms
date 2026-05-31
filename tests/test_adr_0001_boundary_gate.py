# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for scripts/commander/adr-0001-boundary-gate.sh."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "commander" / "adr-0001-boundary-gate.sh"


def _run_gate(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GATE), str(repo)],
        capture_output=True,
        text=True,
        timeout=30,
    )


class AdrBoundaryGateTests(unittest.TestCase):
    def test_clean_repo_passes(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / ".agents").mkdir(parents=True, exist_ok=True)
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn("[RESULT] PASS", result.stdout)

    def test_public_control_surface_is_adr2_allowed(self) -> None:
        # ADR-0002 (accepted 2026-05-08) carves out public/control as an
        # operator-only static surface. The gate must not reject it.
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / "public" / "control").mkdir(parents=True, exist_ok=True)
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn("[RESULT] PASS", result.stdout)
            self.assertNotIn("BOUNDARY_DRIFT: forbidden path present: public/control", result.stdout)

    def test_public_about_surface_fails(self) -> None:
        # Marketing pages under public/ (about, contact, privacy, terms) remain
        # forbidden per ADR-0001 — ADR-0002 does not carve them out.
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / "public" / "about").mkdir(parents=True, exist_ok=True)
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("BOUNDARY_DRIFT: forbidden path present: public/about", result.stdout)

    def test_src_routes_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / "src" / "routes").mkdir(parents=True, exist_ok=True)
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("BOUNDARY_DRIFT: forbidden path present: src/routes", result.stdout)

    def test_autostart_flag_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            (tmp / ".agents").mkdir(parents=True, exist_ok=True)
            (tmp / ".agents" / "config.txt").write_text("autoStart: true\n")
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("BOUNDARY_DRIFT: autoStart activation flag detected", result.stdout)

    def test_autostart_detection_does_not_depend_on_ripgrep(self) -> None:
        gate_text = GATE.read_text(encoding="utf-8")
        self.assertNotIn("rg -n", gate_text)
        self.assertIn("grep", gate_text)


if __name__ == "__main__":
    unittest.main()
