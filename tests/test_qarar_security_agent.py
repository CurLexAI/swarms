# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for the Qarar sovereign security agent."""

from __future__ import annotations

import asyncio

import pytest

from typing import Mapping

from src.agents.security_agent import QararSecurityAgent, SecretScanAssessment


class FakeInferencePort:
    """Mock inference adapter for deterministic unit tests."""

    def __init__(self, response: str = "analysis complete") -> None:
        self.response = response
        self.payloads: list[Mapping[str, object]] = []

    async def generate(self, payload: Mapping[str, object]) -> str:
        """Capture the payload and return the configured response."""

        self.payloads.append(payload)
        return self.response


def test_analyze_incident_builds_sovereign_security_payload() -> None:
    adapter = FakeInferencePort()
    agent = QararSecurityAgent(adapter)

    response = asyncio.run(
        agent.analyze_incident(
            incident_logs="WAF alert: SQL injection attempt against /api/login",
            context_files=["Firewall rule allows only approved private CIDR ranges."],
        )
    )

    assert response == "analysis complete"
    assert len(adapter.payloads) == 1
    payload = adapter.payloads[0]
    assert payload["temperature"] == 0.1
    assert payload["max_tokens"] == 2048
    assert payload["safety_mode"] == "draft_and_escalate"
    prompt = str(payload["prompt"])
    assert "Qarar-Sec" in prompt
    assert "ECC-2:2024" in prompt
    assert "PDPL" in prompt
    assert "Draft-and-Escalate" in prompt
    assert "SQL injection" in prompt


def test_analyze_incident_blocks_secret_like_logs() -> None:
    agent = QararSecurityAgent(FakeInferencePort())

    with pytest.raises(ValueError, match="incident_logs contains secret-like markers"):
        asyncio.run(agent.analyze_incident("leaked token=ghp_example"))


def test_analyze_incident_adds_draft_escalation_to_destructive_output() -> None:
    agent = QararSecurityAgent(FakeInferencePort("Block the source IP immediately."))

    response = asyncio.run(agent.analyze_incident("WAF alert: repeated SQLi attempts"))

    assert response.endswith("Draft-and-Escalate required before destructive action.")


def test_parse_secrets_scan_returns_non_secret_markers_only() -> None:
    agent = QararSecurityAgent(FakeInferencePort())

    assessment = agent.parse_secrets_scan(
        "Finding: GitHub token github_pat_example and API_KEY were detected"
    )

    assert assessment == SecretScanAssessment(
        has_findings=True,
        requires_escalation=True,
        evidence_markers=("api_key", "github_pat", "token"),
    )


def test_parse_secrets_scan_allows_empty_results() -> None:
    agent = QararSecurityAgent(FakeInferencePort())

    assessment = agent.parse_secrets_scan("\n")

    assert assessment == SecretScanAssessment(
        has_findings=False,
        requires_escalation=False,
        evidence_markers=(),
    )
