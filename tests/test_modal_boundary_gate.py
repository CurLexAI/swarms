"""Regression tests for scripts/commander/modal-boundary-gate.sh.

These tests build an isolated temp-repo fixture, copy the gate script
into it, and assert exit codes for the FAIL cases that have already
regressed once (multi-line and backtick Modal imports), plus the PASS
case. They lock the boundary's BEHAVIOR, not its implementation, so
they keep passing across the grep -> python-scanner refactor on PR #49.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "commander" / "modal-boundary-gate.sh"
ADR_GATE = REPO_ROOT / "scripts" / "commander" / "adr-0001-boundary-gate.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "agent-review.yml"


def _build_fixture(tmp: Path) -> None:
    """Provision the minimum files the gate's other checks expect."""
    (tmp / "src").mkdir(parents=True, exist_ok=True)
    (tmp / ".agents" / "router").mkdir(parents=True, exist_ok=True)
    (tmp / ".agents" / "validators").mkdir(parents=True, exist_ok=True)
    (tmp / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (tmp / "scripts" / "commander").mkdir(parents=True, exist_ok=True)
    (tmp / ".agents" / "pr_review.py").write_text("# stub relay\n")
    (tmp / ".agents" / "router" / "__init__.py").write_text("")
    (tmp / ".agents" / "validators" / "__init__.py").write_text("")
    shutil.copy(WORKFLOW, tmp / ".github" / "workflows" / "agent-review.yml")
    shutil.copy(ADR_GATE, tmp / "scripts" / "commander" / "adr-0001-boundary-gate.sh")


def _run_gate(repo: Path) -> subprocess.CompletedProcess:
    # Strip any inherited boundary secrets so [WARN] lines stay deterministic.
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"BAYYINAH_ENDPOINT", "MIHWAR_ENDPOINT", "AGENT_API_TOKEN"}
    }
    return subprocess.run(
        ["bash", str(GATE), str(repo)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


class ModalBoundaryGateTests(unittest.TestCase):
    def test_clean_repo_passes(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "ok.ts").write_text(
                "export const greet = () => 'hello';\n"
            )
            result = _run_gate(tmp)
            self.assertEqual(
                result.returncode,
                0,
                msg=f"expected PASS, got rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("[RESULT] PASS", result.stdout)

    def test_inline_modal_import_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "bad.ts").write_text(
                'import { App } from "modal";\n'
            )
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MODAL_SDK_IMPORT_IN_CLIENT", result.stdout)

    def test_multiline_modal_import_fails(self) -> None:
        # The exact regression class that motivated PR #48: 'from'/'import'
        # and the specifier on different lines. A line-oriented scanner
        # would silently miss this.
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "bad.ts").write_text(
                textwrap.dedent(
                    """\
                    import (
                      "modal"
                    );
                    """
                )
            )
            result = _run_gate(tmp)
            self.assertEqual(
                result.returncode,
                1,
                msg=f"multi-line modal import was NOT detected\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("MODAL_SDK_IMPORT_IN_CLIENT", result.stdout)

    def test_backtick_modal_import_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "bad.ts").write_text(
                "const m = await import(`modal`);\n"
            )
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MODAL_SDK_IMPORT_IN_CLIENT", result.stdout)

    def test_modal_run_url_in_client_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "config.ts").write_text(
                'export const URL = "https://example.modal.run/api";\n'
            )
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MODAL_URL_LEAK", result.stdout)

    def test_modal_run_url_in_build_artifact_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "dist").mkdir(parents=True, exist_ok=True)
            (tmp / "dist" / "bundle.js").write_text('const x = "https://x.modal.run/path";\n')
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MODAL_URL_LEAK_BUILD_ARTIFACT", result.stdout)

    def test_missing_relay_fails(self) -> None:
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / ".agents" / "pr_review.py").unlink()
            (tmp / "src" / "ok.ts").write_text("export const x = 1;\n")
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("RELAY_MISSING", result.stdout)

    def test_boundary_regression_bubbles_up(self) -> None:
        # Verify that an ADR-0001 violation (e.g. src/routes) surfaces as
        # ADR_0001_BOUNDARY_REGRESSION inside the modal gate.
        # Note: public/control is no longer a violation (ADR-0002 allows it).
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "routes").mkdir(parents=True, exist_ok=True)
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ADR_0001_BOUNDARY_REGRESSION", result.stdout)

    @unittest.skipIf(os.name == "nt", "symlinks require admin on Windows")
    def test_symlinked_modal_import_fails(self) -> None:
        # PR #49 P1: a symlinked subdirectory under a public path used to
        # bypass the scan because os.walk's followlinks defaulted False.
        # The scanner now follows symlinks while breaking cycles.
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "ok.ts").write_text("export const x = 1;\n")
            linked = tmp / "linked"
            linked.mkdir()
            (linked / "forbidden.ts").write_text('import "modal";\n')
            os.symlink(linked.resolve(), tmp / "src" / "vendor")
            result = _run_gate(tmp)
            self.assertEqual(
                result.returncode,
                1,
                msg=f"forbidden import behind a symlink was NOT detected\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertIn("MODAL_SDK_IMPORT_IN_CLIENT", result.stdout)

    @unittest.skipIf(os.name == "nt", "symlinks require admin on Windows")
    def test_symlink_cycle_does_not_hang(self) -> None:
        # A cycle like `src/loop -> src` must terminate, not loop forever.
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            _build_fixture(tmp)
            (tmp / "src" / "ok.ts").write_text("export const x = 1;\n")
            os.symlink((tmp / "src").resolve(), tmp / "src" / "loop")
            # _run_gate already imposes a 30s subprocess timeout; if the
            # scanner ever loops, this raises TimeoutExpired.
            result = _run_gate(tmp)
            self.assertEqual(result.returncode, 0)
            self.assertIn("[RESULT] PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
