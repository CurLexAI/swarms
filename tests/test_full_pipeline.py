# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Full local-provider router pipeline tests.

These tests prove the batch-1 sovereign routing contract without contacting any
real model runtime or external provider.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.core.audited_router import build_audited_execution_plan
from src.core.classification import DataClassification, classify_content
from src.core.model_router import route
from src.core.provider_interface import LLMProvider, ProviderError, is_sovereign_local_url
from src.providers.local_llama_cpp import LocalLlamaCppProvider
from src.providers.local_ollama import LocalOllamaProvider


class MockLocalProvider(LLMProvider):
    """Deterministic local provider double used for router tests."""

    def __init__(self, name: str, output: str, healthy: bool = True) -> None:
        self._name = name
        self._output = output
        self._healthy = healthy
        self.generate_calls = 0
        self.health_calls = 0

    async def generate(self, prompt: str, max_tokens: int) -> str:
        """Return deterministic output or fail as unavailable."""

        self.generate_calls += 1
        if not self._healthy:
            raise ProviderError(
                "PROVIDER_UNAVAILABLE",
                self._name,
                "mock local provider unavailable",
            )
        return f"{self._output}:{prompt}:{max_tokens}"

    async def health(self) -> bool:
        """Return configured health state."""

        self.health_calls += 1
        return self._healthy

    def provider_name(self) -> str:
        """Return this mock provider's router key."""

        return self._name


class FullPipelineTests(unittest.TestCase):
    """Integration coverage for local provider routing and audit recording."""


    def test_classifier_uses_exact_hostname_and_precedence_trace(self) -> None:
        decision = classify_content(
            "https://evil.example/sama.gov.sa",
            "public-looking circular",
        )

        self.assertEqual(decision.classification, DataClassification.INTERNAL)
        self.assertIn("default_internal_when_uncertain", decision.reasons)
        self.assertIn(
            "source_hostname_not_allowlisted:evil.example",
            decision.decision_trace,
        )

    def test_classifier_restricted_metadata_overrides_public_source_and_pii(self) -> None:
        decision = classify_content(
            "https://sama.gov.sa/regulations",
            "Customer mobile 0500000000 appears in the sample.",
            {"restricted": True, "sensitivity": "high"},
        )

        self.assertEqual(decision.classification, DataClassification.RESTRICTED)
        self.assertIn("metadata_restricted_true", decision.reasons)
        self.assertIn("sensitive_signal_escalation:CONFIDENTIAL", decision.decision_trace)
        self.assertIn("final_classification:RESTRICTED", decision.decision_trace)

    def test_unknown_classification_blocks_without_provider_call(self) -> None:
        ollama = MockLocalProvider("local_ollama", "unused")
        decision = asyncio.run(
            route(
                "TOP_SECRET",
                "prompt",
                providers={"local_ollama": ollama},
            )
        )

        self.assertEqual(decision.status, "BLOCKED")
        self.assertEqual(decision.blocked_reason, "BLOCKED_UNKNOWN_CLASSIFICATION")
        self.assertIsNone(decision.classification)
        self.assertEqual(ollama.health_calls, 0)

    def test_public_query_routes_to_local_ollama_mock(self) -> None:
        ollama = MockLocalProvider("local_ollama", "ollama-ok")
        llama = MockLocalProvider("local_llama_cpp", "llama-ok")

        decision = asyncio.run(
            route(
                DataClassification.PUBLIC,
                "السلام عليكم",
                max_tokens=64,
                providers={
                    "local_ollama": ollama,
                    "local_llama_cpp": llama,
                },
            )
        )

        self.assertEqual(decision.status, "COMPLETED")
        self.assertEqual(decision.provider_selected, "local_ollama")
        self.assertEqual(decision.response, "ollama-ok:السلام عليكم:64")
        self.assertEqual(ollama.generate_calls, 1)
        self.assertEqual(llama.generate_calls, 0)

    def test_confidential_query_routes_to_local_llama_cpp_only(self) -> None:
        ollama = MockLocalProvider("local_ollama", "ollama-ok")
        llama = MockLocalProvider("local_llama_cpp", "llama-ok")

        decision = asyncio.run(
            route(
                DataClassification.CONFIDENTIAL,
                "تحليل وثيقة سرية",
                providers={
                    "local_ollama": ollama,
                    "local_llama_cpp": llama,
                },
            )
        )

        self.assertEqual(decision.status, "COMPLETED")
        self.assertEqual(decision.provider_selected, "local_llama_cpp")
        self.assertEqual(llama.generate_calls, 1)
        self.assertEqual(ollama.generate_calls, 0)

    def test_local_provider_failure_blocks_without_external_fallback(self) -> None:
        decision = asyncio.run(
            route(
                DataClassification.INTERNAL,
                "internal prompt",
                providers={
                    "local_ollama": MockLocalProvider("local_ollama", "unused", healthy=False),
                    "local_llama_cpp": MockLocalProvider(
                        "local_llama_cpp",
                        "unused",
                        healthy=False,
                    ),
                },
            )
        )

        self.assertEqual(decision.status, "BLOCKED")
        self.assertIsNone(decision.provider_selected)
        self.assertEqual(decision.blocked_reason, "BLOCKED_LOCAL_PROVIDER_UNAVAILABLE")

    def test_audit_events_are_recorded_for_completed_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous_path = os.environ.get("QALA_AUDIT_SINK_PATH")
            audit_path = Path(tmp) / "qala-audit.jsonl"
            os.environ["QALA_AUDIT_SINK_PATH"] = str(audit_path)
            self.addCleanup(self._restore_env, "QALA_AUDIT_SINK_PATH", previous_path)

            plan = asyncio.run(
                build_audited_execution_plan(
                    "public prompt",
                    DataClassification.PUBLIC,
                    "tenant-A",
                    providers={
                        "local_ollama": MockLocalProvider("local_ollama", "ok"),
                        "local_llama_cpp": MockLocalProvider("local_llama_cpp", "unused"),
                    },
                )
            )

            self.assertEqual(plan.route.status, "COMPLETED")
            payload_actions = self._payload_actions(audit_path)
            self.assertEqual(payload_actions, ["classification_decision", "route_decision"])

    def test_audit_events_are_recorded_for_blocked_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous_path = os.environ.get("QALA_AUDIT_SINK_PATH")
            audit_path = Path(tmp) / "qala-audit.jsonl"
            os.environ["QALA_AUDIT_SINK_PATH"] = str(audit_path)
            self.addCleanup(self._restore_env, "QALA_AUDIT_SINK_PATH", previous_path)

            plan = asyncio.run(
                build_audited_execution_plan(
                    "restricted prompt",
                    DataClassification.RESTRICTED,
                    "tenant-B",
                    providers={
                        "local_llama_cpp": MockLocalProvider(
                            "local_llama_cpp",
                            "unused",
                            healthy=False,
                        ),
                    },
                )
            )

            self.assertEqual(plan.route.status, "BLOCKED")
            payload_actions = self._payload_actions(audit_path)
            self.assertEqual(payload_actions, ["classification_decision", "route_blocked"])

    def test_provider_url_validation_rejects_public_hosts(self) -> None:
        self.assertTrue(is_sovereign_local_url("http://ollama:11434"))
        self.assertTrue(is_sovereign_local_url("http://10.0.0.10:8080"))
        self.assertFalse(is_sovereign_local_url("https://api.example.com"))
        with self.assertRaises(ProviderError):
            LocalOllamaProvider(base_url="https://api.example.com")
        with self.assertRaises(ProviderError):
            LocalLlamaCppProvider(base_url="https://api.example.com")

    @staticmethod
    def _restore_env(name: str, previous_value: str | None) -> None:
        if previous_value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous_value

    @staticmethod
    def _payload_actions(path: Path) -> list[str]:
        lines: list[str] = path.read_text(encoding="utf-8").splitlines()
        actions: list[str] = []
        for line in lines:
            record: dict[str, Any] = json.loads(line)
            payload = record["payload"]
            if isinstance(payload, dict):
                action = payload.get("action")
                if isinstance(action, str):
                    actions.append(action)
        return actions


if __name__ == "__main__":
    unittest.main()
