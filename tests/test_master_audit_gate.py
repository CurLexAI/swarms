# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Behavior tests for scripts/commander/master-audit-gate.sh."""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "commander" / "master-audit-gate.sh"


def _run_gate(*, strict: bool) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["MIHWAR_ENDPOINT"] = "http://127.0.0.1:9"
    env["BAYYINAH_ENDPOINT"] = "http://127.0.0.1:9"
    env["ALLOW_EXTERNAL_AI"] = "false"
    env.pop("QALA_AUDIT_SINK_PATH", None)
    if strict:
        env["MASTER_AUDIT_REQUIRE_ENDPOINTS"] = "true"
    else:
        env.pop("MASTER_AUDIT_REQUIRE_ENDPOINTS", None)
    return subprocess.run(
        ["bash", str(GATE), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


class MasterAuditGateTests(unittest.TestCase):
    def test_default_mode_warns_for_unreachable_endpoints(self) -> None:
        result = _run_gate(strict=False)
        self.assertEqual(
            result.returncode,
            0,
            msg=f"expected PASS in non-strict mode, got rc={result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("[WARN] MIHWAR_ENDPOINT_UNREACHABLE: http://127.0.0.1:9", result.stdout)
        self.assertIn("[WARN] BAYYINAH_ENDPOINT_UNREACHABLE: http://127.0.0.1:9", result.stdout)
        self.assertIn("[RESULT] PASS", result.stdout)

    def test_strict_mode_fails_for_unreachable_endpoints(self) -> None:
        result = _run_gate(strict=True)
        self.assertEqual(
            result.returncode,
            1,
            msg=f"expected FAIL in strict mode, got rc={result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("[FAIL] MIHWAR_ENDPOINT_UNREACHABLE: http://127.0.0.1:9", result.stdout)
        self.assertIn("[FAIL] BAYYINAH_ENDPOINT_UNREACHABLE: http://127.0.0.1:9", result.stdout)
        self.assertIn("[RESULT] FAIL", result.stdout)


if __name__ == "__main__":
    unittest.main()
