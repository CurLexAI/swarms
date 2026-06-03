# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Regression tests for Modal endpoint-specific token wiring."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_agent_review_uses_endpoint_specific_tokens() -> None:
    """PR review workflow must not pass the legacy shared token to agents."""

    workflow = _read(".github/workflows/agent-review.yml")

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflow
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflow
    assert "secrets.AGENT_API_TOKEN" not in workflow
    assert "AGENT_API_TOKEN is missing" not in workflow


def test_modal_activation_endpoint_smoke_uses_endpoint_specific_tokens() -> None:
    """Activation smoke must authenticate each endpoint with its own token."""

    workflow = _read(".github/workflows/modal-runtime-activation.yml")

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in workflow
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in workflow
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in workflow
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in workflow
    assert "secrets.AGENT_API_TOKEN" not in workflow
    assert "Authorization: Bearer ${AGENT_API_TOKEN}" not in workflow
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
    assert "secrets.AGENT_API_TOKEN" not in workflow
    assert "Authorization: Bearer ${AGENT_API_TOKEN}" not in workflow
    assert "AGENT_API_TOKEN" not in workflow


def test_modal_boundary_gate_reports_endpoint_specific_tokens() -> None:
    """Boundary gate should report the current endpoint-specific secret names."""

    source = _read("scripts/commander/modal-boundary-gate.sh")

    assert "for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN" in source
    assert "for v in BAYYINAH_ENDPOINT MIHWAR_ENDPOINT AGENT_API_TOKEN" not in source


def test_pr_review_reads_endpoint_specific_tokens() -> None:
    """Python relay must require the same endpoint-specific env contract."""

    source = _read(".agents/pr_review.py")

    assert '_require_env("BAYYINAH_API_TOKEN")' in source
    assert '_require_env("MIHWAR_API_TOKEN")' in source
    assert '_require_env("AGENT_API_TOKEN")' not in source


def test_local_modal_smoke_uses_endpoint_specific_tokens() -> None:
    """Local smoke helper must mirror the activation workflow token contract."""

    script = _read("scripts/commander/modal-runtime-smoke.sh")

    assert "BAYYINAH_API_TOKEN" in script
    assert "MIHWAR_API_TOKEN" in script
    assert "Authorization: Bearer ${token}" in script
    assert "Authorization: Bearer ${AGENT_API_TOKEN}" not in script
    assert "STATUS=BLOCKED_SHARED_ENDPOINT_TOKEN" in script
    assert "STATUS=VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION" in script
    assert "bayyinah-cross-token" in script
    assert "mihwar-cross-token" in script


def test_mcp_server_reads_endpoint_specific_tokens() -> None:
    """MCP dispatch must choose the token that matches the target endpoint."""

    source = _read(".agents/mcp/server.py")

    assert 'os.environ.get("BAYYINAH_API_TOKEN", "")' in source
    assert 'os.environ.get("MIHWAR_API_TOKEN", "")' in source
    assert 'os.environ.get("AGENT_API_TOKEN", "")' not in source
    assert '"AGENT_API_TOKEN is not configured."' not in source


def test_modal_provider_reads_endpoint_specific_tokens() -> None:
    """Provider adapter must not fall back to the legacy shared token."""

    source = _read(".agents/providers/modal_provider.py")

    assert 'return "BAYYINAH_API_TOKEN"' in source
    assert 'return "MIHWAR_API_TOKEN"' in source
    assert 'os.environ.get("AGENT_API_TOKEN", "")' not in source
    assert '"AGENT_API_TOKEN is not configured."' not in source


def test_remote_mcp_surfaces_use_endpoint_specific_tokens() -> None:
    """Render and Cloudflare MCP adapters must keep tokens service-specific."""

    render_blueprint = _read("render.yaml")
    render_config = _read(".agents/mcp/modal-mcp/src/config.ts")
    render_client = _read(".agents/mcp/modal-mcp/src/modalClient.ts")
    cloudflare_agent = _read(".agents/mcp/cloudflare-mcp/src/mcp-agent.ts")
    cloudflare_client = _read(".agents/mcp/cloudflare-mcp/src/modal-client.ts")

    for source in (render_blueprint, render_config, render_client, cloudflare_agent, cloudflare_client):
        assert "AGENT_API_TOKEN" not in source

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


def test_on_demand_swe_workflows_use_endpoint_specific_tokens() -> None:
    """On-demand agent workflows must not use the retired shared token."""

    bayyinah = _read(".github/workflows/bayyinah-swe.yml")
    mihwar = _read(".github/workflows/mihwar-swe.yml")
    free_birds = _read(".github/workflows/free-birds-swe.yml")

    assert "BAYYINAH_API_TOKEN: ${{ secrets.BAYYINAH_API_TOKEN }}" in bayyinah
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in bayyinah
    assert "MIHWAR_API_TOKEN: ${{ secrets.MIHWAR_API_TOKEN }}" in mihwar
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in mihwar
    assert "Authorization: Bearer ${BAYYINAH_API_TOKEN}" in free_birds
    assert "Authorization: Bearer ${MIHWAR_API_TOKEN}" in free_birds

    for workflow in (bayyinah, mihwar, free_birds):
        assert "secrets.AGENT_API_TOKEN" not in workflow
        assert "Authorization: Bearer ${AGENT_API_TOKEN}" not in workflow


def test_pdpl_ingestion_uses_rag_ingest_token_only() -> None:
    """PDPL ingestion workflow must authenticate with the RAG ingest token."""

    workflow = _read(".github/workflows/pdpl-article22-ingestion.yml")

    assert "RAG_INGEST_API_TOKEN: ${{ secrets.RAG_INGEST_API_TOKEN }}" in workflow
    assert "Authorization: Bearer $RAG_INGEST_API_TOKEN" in workflow
    assert "secrets.AGENT_API_TOKEN" not in workflow
    assert "Authorization: Bearer $AGENT_API_TOKEN" not in workflow


def test_rag_modal_endpoints_use_split_tokens_without_legacy_fallback() -> None:
    """RAG Modal endpoints must split ingest/verify auth and reject fallback."""

    source = _read(".agents/ingest_test.py")
    runtime_security = _read(".agents/runtime_security.py")
    modal_app = _read(".agents/modal_app.py")

    assert 'token_env="RAG_INGEST_API_TOKEN"' in source
    assert 'token_env="RAG_VERIFY_API_TOKEN"' in source
    assert 'os.environ.get("AGENT_API_TOKEN", "")' not in source
    assert 'os.environ.get("AGENT_API_TOKEN", "")' not in runtime_security
    assert "allow_legacy_shared_token" not in runtime_security
    assert "ALLOW_LEGACY_SHARED_AGENT_TOKEN" not in runtime_security
    assert "allow_legacy_shared_token" not in modal_app


def test_agent_registry_uses_endpoint_specific_tokens() -> None:
    """Modal registry entries must bind the token matching their endpoint."""

    registry = _read("agents/registry.yaml")

    assert 'token_env: "AGENT_API_TOKEN"' not in registry
    assert 'endpoint_env: "BAYYINAH_ENDPOINT"\n      token_env: "BAYYINAH_API_TOKEN"' in registry
    assert 'endpoint_env: "MIHWAR_ENDPOINT"\n      token_env: "MIHWAR_API_TOKEN"' in registry
