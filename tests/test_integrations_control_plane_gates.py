# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for no-secrets integration control-plane gates."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_render_blueprint_is_manual_gated_and_uses_secret_sync() -> None:
    """Render must remain a manual, no-hook deployment boundary."""

    render_yaml = read_text("render.yaml")

    assert "autoDeploy: false" in render_yaml
    assert "healthCheckPath: /healthz" in render_yaml
    assert "name: SR.BSM" in render_yaml
    assert "rootDir: ." in render_yaml
    assert "buildCommand: npm ci --include=dev && npm run test:render-public && npm run check:cdn-sri" in render_yaml
    assert "startCommand: npm start" in render_yaml
    assert "port: 10000" in render_yaml
    assert "api.render.com/deploy" not in render_yaml
    assert "deploy hook" not in render_yaml.lower()
    for secret_name in (
        "MCP_BEARER_TOKEN",
        "MODAL_API_TOKEN",
        "MIHWAR_ENDPOINT",
        "BAYYINAH_ENDPOINT",
        "MIHWAR_API_TOKEN",
        "BAYYINAH_API_TOKEN",
    ):
        assert secret_name not in render_yaml


def test_render_deploy_is_separate_manual_environment_gate() -> None:
    """Render deploy authority must live only in the manual production workflow."""

    deploy = read_text(".github/workflows/render-deploy.yml")
    fastconnect = read_text(".github/workflows/qarar-fastconnect-deploy.yml")

    assert "workflow_dispatch:" in deploy
    assert "environment: production" in deploy
    assert "confirm_manual_gated_deploy == 'DEPLOY'" in deploy
    assert "secrets.RENDER_DEPLOY_HOOK_URL" in deploy
    assert "vars.RENDER_DEPLOY_HOOK_URL" not in deploy
    assert "api.render.com/v1/services" not in fastconnect
    assert "RENDER_API_KEY" not in fastconnect
    assert "RENDER_SERVICE_ID" not in fastconnect



def test_copilot_mcp_default_is_offline_no_secrets_python3() -> None:
    """GitHub Copilot MCP must default to the offline no-secrets server."""

    config = json.loads(read_text(".github/copilot/mcp.json"))
    server = config["mcpServers"]["qarar-offline-mcp"]

    assert server["type"] == "local"
    assert server["command"] == "python3"
    assert server["args"] == ["-u", ".agents/mcp/server_offline.py"]
    assert "env" not in server
    assert set(server["tools"]) == {
        "repo_static_audit",
        "mihwar_generate_offline",
        "bayyinah_review_offline",
        "qarar_agent_registry_suggest",
    }


def test_modal_qdrant_surface_is_snapshot_only_and_not_volume_backed_live_storage() -> None:
    """Modal Qdrant wrapper must expose only health/snapshot and persist snapshots only."""

    source = read_text("modal/qarar_rag_infra.py")
    tree = ast.parse(source)
    routes: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            routes.add((func.attr, str(decorator.args[0].value)))

    assert ("get", "/health") in routes
    assert ("post", "/snapshot") in routes
    assert ("post", "/ingest") not in routes
    assert ("post", "/search") not in routes
    assert not any(route for route in routes if "collections" in route[1])
    assert 'volumes={"/snapshots": volume}' in source
    assert 'volumes={"/qdrant' not in source
    assert 'LOCAL_STORAGE = Path("/qdrant/storage")' in source
    assert 'SNAPSHOT_DIR = Path("/snapshots")' in source
    assert "LOCAL_STORAGE = Path(\"/qdrant/storage\")" in source
    assert "SNAPSHOT_DIR = Path(\"/snapshots\")" in source


def test_static_audit_has_no_external_tool_dependency_and_fails_on_findings(tmp_path: Path) -> None:
    """Secret scan must be pure Python and fail closed when a pattern is found."""

    source = read_text("scripts/security/static_audit.py")
    assert "subprocess" not in source
    assert "command -v rg" not in source
    assert "rglob" in source

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "static_audit", REPO_ROOT / "scripts/security/static_audit.py"
    )
    assert spec is not None and spec.loader is not None
    import sys

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    secret_file = tmp_path / "leak.py"
    token = "ghp_" + "123456789012345678901234567890123456"
    secret_file.write_text(f'TOKEN = "{token}"\n', encoding="utf-8")

    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["static_audit.py", str(tmp_path)]
        assert module.main() == 1
    finally:
        sys.argv = original_argv


def test_runtime_policy_check_script_exists_for_aggregate_gate() -> None:
    """Aggregate npm check must have a concrete canonical runtime policy script."""

    script = read_text("scripts/check-runtime-policy.ts")
    assert "evaluateRuntimePolicy" in script
    assert "selectRuntimeProviders" not in script
    assert "Runtime policy check passed." in script


def test_no_secrets_preflight_workflows_do_not_require_runtime_secrets() -> None:
    """Preflight checks must not require private runtime secrets."""

    preflight_workflows = [
        ".github/workflows/aegis-gate.yml",
        ".github/workflows/aegis-mcp-gateway.yml",
        ".github/workflows/secret-scan.yml",
        ".github/workflows/constitutional-compliance.yml",
        ".github/workflows/render-preflight.yml",
    ]
    for workflow in preflight_workflows:
        content = read_text(workflow)
        assert "secrets.BAYYINAH_ENDPOINT" not in content
        assert "secrets.MIHWAR_ENDPOINT" not in content
        assert "secrets." + "AGENT" + "_API_TOKEN" not in content
        assert "secrets.RENDER_DEPLOY_HOOK_URL" not in content

    assert "python3 -m unittest tests.test_aegis_mcp_gateway" in read_text(
        ".github/workflows/aegis-mcp-gateway.yml"
    )
    assert "python3 -m pip install --upgrade pip" in read_text(
        ".github/workflows/constitutional-compliance.yml"
    )


def test_copilot_custom_agent_profiles_use_agent_suffix_only() -> None:
    """Copilot custom agents must use only the canonical .agent.md profile names."""

    agents_dir = REPO_ROOT / ".github" / "agents"
    profiles = sorted(path.name for path in agents_dir.glob("*"))

    assert profiles == [
        "bayyinah.agent.md",
        "core-coding-swarm.agent.md",
        "free-birds.agent.md",
        "mihwar.agent.md",
        "qarar-platform-supervisor.agent.md",
    ]


def test_recovery_supervisor_is_renamed_and_propose_only() -> None:
    """Recovery supervisor must not retain unsafe naming or execution authority."""

    registry = read_text(".agents/registries/recovery-supervisor.yaml")
    prompt = read_text(".agents/prompts/recovery-supervisor.md")

    assert "kamikaze" not in registry.lower()
    assert "kamikaze" not in prompt.lower()
    assert "status: proposed" in registry
    assert "execute_can: false" in registry
    assert "propose_patch" in registry
    assert "open_pull_request" not in registry
    assert "call_render_deploy_hook" in registry
    assert "call_modal_deploy" in registry


def test_swarm_presence_no_network_json_is_preflight_safe() -> None:
    """No-network swarm presence must serialize JSON and not fail preflight on skipped external checks."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "swarm_presence_monitor", REPO_ROOT / "scripts/commander/swarm-presence-monitor.py"
    )
    assert spec is not None and spec.loader is not None
    import sys

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    report = module.SwarmPresenceMonitor(REPO_ROOT, "CurLexAI/swarms", no_network=True).run(strict=False)
    payload = json.loads(report.to_json())

    assert payload["exitCode"] == 0
    assert payload["summary"]["SKIPPED_UNVERIFIED"] >= 1
    assert all("evidence" in check for check in payload["checks"])
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
    """Render deploy authority must live in the dedicated manual workflow only."""

    workflow = read_repo_text(".github/workflows/render-deploy.yml")
    fastconnect = read_repo_text(".github/workflows/qarar-fastconnect-deploy.yml")

    assert "workflow_dispatch:" in workflow
    assert "confirm_manual_gated_deploy" in workflow
    assert "confirm_manual_gated_deploy == 'DEPLOY'" in workflow
    assert "environment: production" in workflow
    assert "secrets.RENDER_DEPLOY_HOOK_URL" in workflow
    assert "push:" not in workflow
    assert "pull_request:" not in workflow
    assert "api.render.com/v1/services" not in fastconnect
    assert "RENDER_API_KEY" not in fastconnect
    assert "RENDER_SERVICE_ID" not in fastconnect


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
