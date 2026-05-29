# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Integration tests for the SAMA ingestion swarm."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from sama_ingestion_swarm.agent_auditor import AuditDecision, SamaAuditor, SecurityScanResult
from sama_ingestion_swarm.agent_fetcher import SamaFetcher
from sama_ingestion_swarm.agent_parser import ParsedArticle, SamaParser, normalize_arabic
from sama_ingestion_swarm.orchestrator import SamaIngestionOrchestrator


class MemoryObjectStore:
    """In-memory object-store test double."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    async def get_object(self, bucket: str, key: str) -> bytes:
        return self.objects[(bucket, key)][0]


class FakeSecurityGate:
    """Deterministic security gate test double."""

    def __init__(self, verdict: str) -> None:
        self._verdict = verdict
        self.scanned: list[ParsedArticle] = []

    async def scan(self, article: ParsedArticle) -> SecurityScanResult:
        self.scanned.append(article)
        if self._verdict == "ALLOW":
            return SecurityScanResult(verdict="ALLOW")
        return SecurityScanResult(verdict="QUARANTINE", reasons=("PII_DETECTED",))


class FakeVectorIndexer:
    """Qdrant indexer test double."""

    def __init__(self) -> None:
        self.indexed: list[ParsedArticle] = []

    async def upsert_article(self, article: ParsedArticle) -> None:
        self.indexed.append(article)


class FakeTextIndexer:
    """OpenSearch indexer test double."""

    def __init__(self) -> None:
        self.indexed: list[ParsedArticle] = []

    async def index_article(self, article: ParsedArticle) -> None:
        self.indexed.append(article)


class SamaSwarmTests(unittest.TestCase):
    """SAMA swarm integration contract tests."""

    def setUp(self) -> None:
        self._previous_audit_path = os.environ.get("QALA_AUDIT_SINK_PATH")
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["QALA_AUDIT_SINK_PATH"] = str(Path(self._tmp.name) / "audit.jsonl")

    def tearDown(self) -> None:
        if self._previous_audit_path is None:
            os.environ.pop("QALA_AUDIT_SINK_PATH", None)
        else:
            os.environ["QALA_AUDIT_SINK_PATH"] = self._previous_audit_path
        self._tmp.cleanup()

    def test_full_pipeline_fetch_parse_audit_index(self) -> None:
        store = MemoryObjectStore()
        gate = FakeSecurityGate("ALLOW")
        qdrant = FakeVectorIndexer()
        opensearch = FakeTextIndexer()
        orchestrator = self._build_orchestrator(store, gate, qdrant, opensearch)

        result = asyncio.run(orchestrator.run_once(["https://www.sama.gov.sa/rules.html"]))

        self.assertEqual(len(result.documents), 1)
        document = result.documents[0]
        self.assertEqual(document.errors, ())
        self.assertIsNotNone(document.fetched)
        self.assertIsNotNone(document.parsed)
        self.assertEqual(len(qdrant.indexed), 2)
        self.assertEqual(len(opensearch.indexed), 2)
        self.assertEqual([decision.verdict for decision in document.audit_decisions], ["ALLOW", "ALLOW"])
        self.assertIn("pipeline_start", self._audit_actions())
        self.assertIn("pipeline_complete", self._audit_actions())
        self.assertIn("sama_audit_decision", self._audit_actions())

    def test_quarantine_path_creates_ticket_and_does_not_index(self) -> None:
        store = MemoryObjectStore()
        gate = FakeSecurityGate("QUARANTINE")
        qdrant = FakeVectorIndexer()
        opensearch = FakeTextIndexer()
        orchestrator = self._build_orchestrator(store, gate, qdrant, opensearch)

        result = asyncio.run(orchestrator.run_once(["https://www.sama.gov.sa/rules.html"]))

        self.assertEqual(result.documents[0].errors, ())
        self.assertEqual(qdrant.indexed, [])
        self.assertEqual(opensearch.indexed, [])
        decisions: tuple[AuditDecision, ...] = result.documents[0].audit_decisions
        self.assertTrue(all(decision.verdict == "QUARANTINE" for decision in decisions))
        ticket_keys = [key for bucket, key in store.objects if bucket == "quarantine"]
        self.assertEqual(len(ticket_keys), 2)

    def test_fetcher_domain_allowlist(self) -> None:
        fetcher = SamaFetcher(
            object_store=MemoryObjectStore(),
            bucket="raw",
            allowed_domains=("www.sama.gov.sa",),
            http_transport=self._transport(),
        )

        with self.assertRaises(ValueError):
            fetcher.validate_source_url("https://evil.example/rules.html")
        with self.assertRaises(ValueError):
            fetcher.validate_source_url("http://www.sama.gov.sa/rules.html")

    def test_parser_arabic_normalization(self) -> None:
        text = "المـادة الأولى: إلتزام الجهة. المادة الثانية: مسؤولية المنشأة."
        normalized = normalize_arabic(text)

        self.assertNotIn("ـ", normalized)
        self.assertIn("الماده الاولي", normalized)
        self.assertIn("مسؤوليه المنشاه", normalized)

    def _build_orchestrator(
        self,
        store: MemoryObjectStore,
        gate: FakeSecurityGate,
        qdrant: FakeVectorIndexer,
        opensearch: FakeTextIndexer,
    ) -> SamaIngestionOrchestrator:
        fetcher = SamaFetcher(
            object_store=store,
            bucket="raw",
            allowed_domains=("www.sama.gov.sa",),
            http_transport=self._transport(),
        )
        parser = SamaParser(object_store=store, parsed_bucket="parsed")
        auditor = SamaAuditor(
            security_gate=gate,
            vector_indexer=qdrant,
            text_indexer=opensearch,
            object_store=store,
            quarantine_bucket="quarantine",
        )
        return SamaIngestionOrchestrator(fetcher=fetcher, parser=parser, auditor=auditor)

    @staticmethod
    def _transport() -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            html = """
            <html><body>
            <h1>لائحة</h1>
            <p>المادة الأولى: يجب الالتزام بالتعليمات.</p>
            <p>المادة الثانية: تطبق المتطلبات على الجهات.</p>
            </body></html>
            """.encode("utf-8")
            return httpx.Response(200, headers={"content-type": "text/html"}, content=html)

        return httpx.MockTransport(handler)

    def _audit_actions(self) -> list[str]:
        path = Path(os.environ["QALA_AUDIT_SINK_PATH"])
        actions: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            record: Mapping[str, Any] = json.loads(line)
            payload = record.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("action"), str):
                actions.append(payload["action"])
        return actions


if __name__ == "__main__":
    unittest.main()
