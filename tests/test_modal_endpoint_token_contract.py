# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for Modal endpoint-specific token wiring."""

from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

LEGACY_SHARED_TOKEN_ENV = "AGENT" + "_API_TOKEN"
LEGACY_SHARED_SECRET_REF = f"secrets.{LEGACY_SHARED_TOKEN_ENV}"
LEGACY_SHARED_BEARER = f"Authorization: Bearer ${{{LEGACY_SHARED_TOKEN_ENV}}}"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _load_runtime_security_module() -> ModuleType:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "runtime_security", REPO_ROOT / ".agents" / "runtime_security.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assert_rejects_cross_token(module: ModuleType, token_env: str, wrong_token: str) -> None:
    from fastapi import HTTPException

    try:
        module.verify_bearer_token(f"Bearer {wrong_token}", token_env=token_env)
    except HTTPException as error:
        assert error.status_code == 401
        assert error.detail == "invalid_token"
    else:
        raise AssertionError(f"{token_env} accepted another endpoint token")


def test_agent_review_uses_endpoint_specific_tokens() -> None:
    """PR review workflow must not pass the legacy shared token to agents."""

    workflow = _read(".github/workflows/agent-review.yml")

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflow
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflow
    assert LEGACY_SHARED_SECRET_REF not in workflow
    assert f"{LEGACY_SHARED_TOKEN_ENV} is missing" not in workflow


def test_modal_activation_endpoint_smoke_uses_endpoint_specific_tokens() -> None:
    """Activation smoke must authenticate each endpoint with its own token."""

    workflow = _read(".github/workflows/modal-runtime-activation.yml")

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflow
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflow
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in workflow
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in workflow
    assert LEGACY_SHARED_SECRET_REF not in workflow
    assert LEGACY_SHARED_BEARER not in workflow
    assert "BLOCKED_SHARED_ENDPOINT_TOKEN" in workflow
    assert "VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION" in workflow
    assert "bayyinah_cross_status" in workflow
    assert "mihwar_cross_status" in workflow


def test_smoke_modal_uses_endpoint_specific_tokens() -> None:
    """Manual smoke probe must match the hardened endpoint token contract."""

    workflow = _read(".github/workflows/smoke-modal.yml")

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflow
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflow
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in workflow
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in workflow
    assert LEGACY_SHARED_SECRET_REF not in workflow
    assert LEGACY_SHARED_BEARER not in workflow
    assert LEGACY_SHARED_TOKEN_ENV not in workflow


def test_modal_boundary_gate_reports_endpoint_specific_tokens() -> None:
    """Boundary gate should report the current endpoint-specific secret names."""

    source = _read("scripts/commander/modal-boundary-gate.sh")

    assert "for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN" in source
    assert "for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT " + LEGACY_SHARED_TOKEN_ENV not in source


def test_pr_review_reads_endpoint_specific_tokens() -> None:
    """Python relay must require the same endpoint-specific env contract."""

    source = _read(".agents/pr_review.py")

    assert '_require_env("BAYYINAH_API_TOKEN")' in source
    assert '_require_env("MIHWAR_API_TOKEN")' in source
    assert f'_require_env("{LEGACY_SHARED_TOKEN_ENV}")' not in source


def test_local_modal_smoke_uses_endpoint_specific_tokens() -> None:
    """Local smoke helper must mirror the activation workflow token contract."""

    script = _read("scripts/commander/modal-runtime-smoke.sh")

    assert "BAYYINAH_API_TOKEN" in script
    assert "MIHWAR_API_TOKEN" in script
    assert "Authorization: Bearer ${token}" in script
    assert LEGACY_SHARED_BEARER not in script
    assert "STATUS=BLOCKED_SHARED_ENDPOINT_TOKEN" in script
    assert "STATUS=VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION" in script
    assert "bayyinah-cross-token" in script
    assert "mihwar-cross-token" in script


def test_mcp_server_reads_endpoint_specific_tokens() -> None:
    """MCP dispatch must choose the token that matches the target endpoint."""

    source = _read(".agents/mcp/server.py")

    assert 'os.environ.get("BAYYINAH_API_TOKEN", "")' in source
    assert 'os.environ.get("MIHWAR_API_TOKEN", "")' in source
    assert f'os.environ.get("{LEGACY_SHARED_TOKEN_ENV}", "")' not in source
    assert f'"{LEGACY_SHARED_TOKEN_ENV} is not configured."' not in source


def test_modal_provider_reads_endpoint_specific_tokens() -> None:
    """Provider adapter must not fall back to the legacy shared token."""

    source = _read(".agents/providers/modal_provider.py")

    assert 'return "BAYYINAH_API_TOKEN"' in source
    assert 'return "MIHWAR_API_TOKEN"' in source
    assert f'os.environ.get("{LEGACY_SHARED_TOKEN_ENV}", "")' not in source
    assert f'"{LEGACY_SHARED_TOKEN_ENV} is not configured."' not in source


def test_remote_mcp_surfaces_use_endpoint_specific_tokens() -> None:
    """Render and Cloudflare MCP adapters must keep tokens service-specific."""

    render_blueprint = _read("render.yaml")
    render_config = _read(".agents/mcp/modal-mcp/src/config.ts")
    render_client = _read(".agents/mcp/modal-mcp/src/modalClient.ts")
    cloudflare_agent = _read(".agents/mcp/cloudflare-mcp/src/mcp-agent.ts")
    cloudflare_client = _read(".agents/mcp/cloudflare-mcp/src/modal-client.ts")

    for source in (render_blueprint, render_config, render_client, cloudflare_agent, cloudflare_client):
        assert LEGACY_SHARED_TOKEN_ENV not in source

    assert "MIHWAR_API_TOKEN" in render_blueprint
    assert "BAYYINAH_API_TOKEN" in render_blueprint
    assert "mihwarApiToken: env.MIHWAR_API_TOKEN" in render_config
    assert "bayyinahApiToken: env.BAYYINAH_API_TOKEN" in render_config
    assert "this.config.mihwarApiToken" in render_client
    assert "this.config.bayyinahApiToken" in render_client
    assert "this.env.MIHWAR_API_TOKEN" in cloudflare_agent
    assert "this.env.BAYYINAH_API_TOKEN" in cloudflare_agent
    assert "config.mihwarApiToken" in cloudflare_client
    assert "config.bayyinahApiToken" in cloudflare_client


def test_runtime_security_has_no_legacy_shared_token_fallback() -> None:
    """Modal runtime auth must not accept the deprecated shared token path."""

    source = _read(".agents/runtime_security.py")

    assert LEGACY_SHARED_TOKEN_ENV not in source
    assert "ALLOW_LEGACY_SHARED_" + "AGENT_TOKEN" not in source
    assert "allow_legacy_shared_token" not in source
    assert 'os.environ.get(token_env, "")' in source


def test_modal_app_does_not_expose_legacy_shared_token_opt_in() -> None:
    """Modal endpoint wiring must not document or pass a legacy-token opt-in."""

    source = _read(".agents/modal_app.py")

    assert LEGACY_SHARED_TOKEN_ENV not in source
    assert "ALLOW_LEGACY_SHARED_" + "AGENT_TOKEN" not in source
    assert "allow_legacy_shared_token" not in source
    assert 'token_env="BAYYINAH_API_TOKEN"' in source
    assert 'token_env="MIHWAR_API_TOKEN"' in source


def test_on_demand_agent_workflows_use_endpoint_specific_tokens() -> None:
    """Slash-command agent workflows must not authorize with a shared token."""

    workflows = {
        "bayyinah": _read(".github/workflows/bayyinah-swe.yml"),
        "mihwar": _read(".github/workflows/mihwar-swe.yml"),
        "free_birds": _read(".github/workflows/free-birds-swe.yml"),
    }

    for source in workflows.values():
        assert LEGACY_SHARED_SECRET_REF not in source
        assert LEGACY_SHARED_BEARER not in source
        assert LEGACY_SHARED_TOKEN_ENV not in source

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflows["bayyinah"]
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in workflows["bayyinah"]
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflows["mihwar"]
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in workflows["mihwar"]
    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflows["free_birds"]
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflows["free_birds"]
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in workflows["free_birds"]
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in workflows["free_birds"]


def test_modal_activation_verifies_token_isolation_negative_smoke() -> None:
    """Runtime activation must prove each endpoint rejects the other endpoint token."""

    workflow = _read(".github/workflows/modal-runtime-activation.yml")

    assert "BLOCKED_SHARED_ENDPOINT_TOKEN" in workflow
    assert "cross-token-negative-smoke" in workflow
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in workflow
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in workflow
    assert "VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION" in workflow


def test_modal_endpoint_tokens_reject_cross_endpoint_bearers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bayyinah and Mihwar must reject each other's endpoint token."""

    module = _load_runtime_security_module()
    monkeypatch.setenv("BAYYINAH_API_TOKEN", "bayyinah-only-token")
    monkeypatch.setenv("MIHWAR_API_TOKEN", "mihwar-only-token")

    module.verify_bearer_token(
        "Bearer bayyinah-only-token", token_env="BAYYINAH_API_TOKEN"
    )
    module.verify_bearer_token(
        "Bearer mihwar-only-token", token_env="MIHWAR_API_TOKEN"
    )
    _assert_rejects_cross_token(module, "BAYYINAH_API_TOKEN", "mihwar-only-token")
    _assert_rejects_cross_token(module, "MIHWAR_API_TOKEN", "bayyinah-only-token")


def test_rag_endpoint_tokens_reject_cross_endpoint_bearers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RAG ingest and verify endpoints must reject each other's token."""

    module = _load_runtime_security_module()
    monkeypatch.setenv("RAG_INGEST_API_TOKEN", "rag-ingest-only-token")
    monkeypatch.setenv("RAG_VERIFY_API_TOKEN", "rag-verify-only-token")

    module.verify_bearer_token(
        "Bearer rag-ingest-only-token", token_env="RAG_INGEST_API_TOKEN"
    )
    module.verify_bearer_token(
        "Bearer rag-verify-only-token", token_env="RAG_VERIFY_API_TOKEN"
    )
    _assert_rejects_cross_token(module, "RAG_INGEST_API_TOKEN", "rag-verify-only-token")
    _assert_rejects_cross_token(module, "RAG_VERIFY_API_TOKEN", "rag-ingest-only-token")


def test_qdrant_auth_is_required_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Qdrant break-glass must not bypass production API-key auth."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "runtime_security", REPO_ROOT / ".agents" / "runtime_security.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_QDRANT", "true")
    monkeypatch.setenv("QDRANT_INTERNAL_URL", "http://qdrant:6333")
    monkeypatch.setenv("NODE_ENV", "production")

    try:
        module.require_qdrant_auth()
    except RuntimeError as error:
        assert str(error) == "qdrant_api_key_required_in_production"
    else:
        raise AssertionError("production Qdrant auth bypass was accepted")


def test_qdrant_break_glass_is_local_private_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unauthenticated Qdrant is accepted only for local/dev private-network use."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "runtime_security", REPO_ROOT / ".agents" / "runtime_security.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    monkeypatch.delenv("QDRANT_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_UNAUTHENTICATED_QDRANT", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("QDRANT_INTERNAL_URL", "http://127.0.0.1:6333")

    module.require_qdrant_auth()

    monkeypatch.setenv("QDRANT_INTERNAL_URL", "https://qdrant.example.invalid")
    try:
        module.require_qdrant_auth()
    except RuntimeError as error:
        assert str(error) == "qdrant_unauthenticated_requires_private_network"
    else:
        raise AssertionError("reachable Qdrant auth bypass was accepted")
