# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for no-secrets integration control-plane gates."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo_text(relative_path: str) -> str:
    """Read a repository text file for static workflow assertions.

    Args:
        relative_path: Repository-relative path to read.

    Returns:
        UTF-8 decoded file content.
    """

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_secret_static_audit_fails_closed_for_missing_target() -> None:
    """The local secret scanner must not pass silently for a bad path."""

    result = subprocess.run(
        [sys.executable, "scripts/security/static_audit.py", "does-not-exist-for-audit"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "does not exist" in result.stderr


def test_copilot_mcp_defaults_to_python3_offline_server() -> None:
    """Copilot MCP config must keep no-secrets offline mode as the default."""

    config = read_repo_text(".github/copilot/mcp.json")

    assert '"qarar-offline-mcp"' in config
    assert '"command": "python3"' in config
    assert ".agents/mcp/server_offline.py" in config
    assert "MIHWAR_ENDPOINT" not in config
    assert "BAYYINAH_ENDPOINT" not in config


def test_modal_deploy_workflow_is_manual_and_confirmed() -> None:
    """Modal deployment must be manual and guarded by an explicit phrase."""

    workflow = read_repo_text(".github/workflows/modal-deploy.yml")

    assert "workflow_dispatch:" in workflow
    assert "confirm_deploy:" in workflow
    assert "DEPLOY_MODAL" in workflow
    assert "push:" not in workflow
    assert "modal deploy modal/qarar_rag_infra.py" in workflow


def test_render_deploy_job_is_manual_confirmed_and_secret_gated() -> None:
    """Render deploy must not run from an automatic push path."""

    workflow = read_repo_text(".github/workflows/qarar-fastconnect-deploy.yml")

    assert "pull_request:" in workflow
    assert "deploy_render:" in workflow
    assert "DEPLOY_RENDER" in workflow
    assert "if: github.event_name == 'workflow_dispatch'" in workflow
    assert "Required Render deployment secrets are missing." in workflow
    assert "https://api.render.com/v1/services/${RENDER_SERVICE_ID}/deploys" in workflow


def test_agent_presence_gate_does_not_require_ripgrep() -> None:
    """Agent presence gate must not depend on rg being installed."""

    gate = read_repo_text("scripts/commander/agent-presence-gate.sh")

    assert "rg -n" not in gate
    assert "grep -E -n" in gate


def test_agent_presence_gate_runs_when_rg_is_absent(tmp_path: Path) -> None:
    """The agent presence gate should pass with a PATH that excludes rg."""

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    os.symlink("/usr/bin/grep", bin_dir / "grep")

    result = subprocess.run(
        ["/usr/bin/bash", "scripts/commander/agent-presence-gate.sh"],
        cwd=REPO_ROOT,
        env={"PATH": str(bin_dir), "PYTHON_BIN": sys.executable},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK] configured_agent_count=" in result.stdout


def test_swarm_presence_no_network_json_is_non_blocking() -> None:
    """The aggregate no-secrets check must serialize slots dataclasses and not fail on skipped network checks."""

    result = subprocess.run(
        [
            sys.executable,
            "scripts/commander/swarm-presence-monitor.py",
            "--repo-root",
            ".",
            "--no-network",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"SKIPPED_UNVERIFIED"' in result.stdout
    assert '"exitCode": 0' in result.stdout
