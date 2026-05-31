# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for integration deployment workflow boundaries."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def read_workflow(name: str) -> str:
    """Return a workflow file as UTF-8 text.

    Args:
        name: Workflow file name under ``.github/workflows``.

    Returns:
        The workflow file content.
    """

    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_render_preflight_is_no_secrets_and_no_deploy() -> None:
    """Ensure Render preflight remains safe for PR and push events."""

    text = read_workflow("render-preflight.yml")

    assert "pull_request:" in text
    assert "push:" in text
    assert "workflow_dispatch:" in text
    assert "secrets." not in text
    assert "RENDER_DEPLOY_HOOK_URL" not in text
    assert "curl " not in text
    assert "npm ci --include=dev" in text

    render_yaml = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "autoDeploy: false" in render_yaml


def test_render_deploy_is_manual_production_environment_only() -> None:
    """Ensure Render deployment is manual, production-gated, and secret-backed."""

    text = read_workflow("render-deploy.yml")

    assert "workflow_dispatch:" in text
    assert "pull_request:" not in text
    assert "push:" not in text
    assert "environment: production" in text
    assert "confirm_manual_gated_deploy == 'DEPLOY'" in text
    assert "secrets.RENDER_DEPLOY_HOOK_URL" in text
    assert "vars.RENDER_DEPLOY_HOOK_URL" not in text
    assert "curl --fail --silent --show-error --request POST" in text


def test_fastconnect_workflow_cannot_deploy_render() -> None:
    """Ensure the FastConnect workflow is a build preflight, not a Render deploy path."""

    text = read_workflow("qarar-fastconnect-deploy.yml")

    forbidden_markers = (
        "RENDER_API_KEY",
        "RENDER_SERVICE_ID",
        "api.render.com/v1/services",
        "Deploy via Render API",
        "deploy-render:",
    )
    for marker in forbidden_markers:
        assert marker not in text
    assert "Build Preflight" in text
    assert "render-deploy.yml" in text


def test_copilot_setup_installs_dev_dependencies_and_avoids_live_integrations() -> None:
    """Ensure Copilot setup uses local no-secrets checks instead of live integration tests."""

    text = read_workflow("copilot-setup-steps.yml")

    assert "npm ci --include=dev" in text
    assert "npm run check --if-present" in text
    assert "npm test --if-present" in text


def test_swarm_presence_monitor_no_network_json_is_nonblocking() -> None:
    """Ensure no-network presence evidence stays JSON-serializable and check-friendly."""

    import json
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts/commander/swarm-presence-monitor.py",
            "--repo-root",
            ".",
            "--no-network",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["summary"]["FAILED"] == 0
    assert report["summary"]["HOLD"] == 0
    assert report["summary"]["SKIPPED_UNVERIFIED"] >= 1
    assert report["exitCode"] == 0


def test_release_readiness_uses_strict_presence_monitor() -> None:
    """Ensure readiness gates do not treat no-network presence checks as launch evidence."""

    package_json = (REPO_ROOT / "package.json").read_text(encoding="utf-8")
    release_gate = (REPO_ROOT / "scripts" / "commander" / "release-readiness-gate.sh").read_text(
        encoding="utf-8"
    )

    assert "check:swarms-presence:strict" in package_json
    assert "--strict" in package_json
    assert "Strict swarm presence monitor" in release_gate
    assert "npm run check:swarms-presence:strict" in release_gate
