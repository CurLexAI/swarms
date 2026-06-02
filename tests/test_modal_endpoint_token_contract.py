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
