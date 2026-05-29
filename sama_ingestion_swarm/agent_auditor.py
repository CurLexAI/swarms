"""SAMA auditor/indexer agent for security-gated regulatory articles."""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Mapping
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from sama_ingestion_swarm import record_audit_event
from sama_ingestion_swarm.agent_parser import ParseResult, ParsedArticle
from src.core.audited_router import QalaAuditAdapter

GateVerdict = Literal["ALLOW", "QUARANTINE", "BLOCK"]


class ObjectStore(Protocol):
    """Async object-store port for quarantine review tickets."""

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Write a review-ticket object."""


class SecurityGate(Protocol):
    """DLP/PII security gate port."""

    async def scan(self, article: ParsedArticle) -> "SecurityScanResult":
        """Scan a parsed article and return a gate verdict."""


class VectorIndexer(Protocol):
    """Qdrant/vector indexer port."""

    async def upsert_article(self, article: ParsedArticle) -> None:
        """Upsert an article into vector search."""


class TextIndexer(Protocol):
    """OpenSearch/text indexer port."""

    async def index_article(self, article: ParsedArticle) -> None:
        """Index an article into text search."""


class SecurityScanResult(BaseModel):
    """Result returned by the internal qarar-security-gate service."""

    verdict: GateVerdict
    reasons: tuple[str, ...] = ()


class AuditDecision(BaseModel):
    """Auditor decision for one parsed article."""

    article_number: str | None = None
    source_hash: str = Field(min_length=64, max_length=64)
    verdict: GateVerdict
    indexed: bool
    quarantine_ticket_key: str | None = None


def _validate_internal_gate_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    if parsed.scheme != "https":
        raise ValueError("qarar-security-gate URL must use HTTPS/mTLS")
    if "." in host and not host.endswith((".internal", ".local", ".svc", ".cluster.local")):
        raise ValueError("qarar-security-gate URL must be internal")
    return base_url.rstrip("/")


class HttpSecurityGate:
    """HTTP adapter for the internal ``qarar-security-gate /scan`` endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        configured_url = base_url or os.environ.get(
            "QARAR_SECURITY_GATE_URL",
            "https://qarar-security-gate:8443",
        )
        self._base_url = _validate_internal_gate_url(configured_url)
        self._http_transport = http_transport

    async def scan(self, article: ParsedArticle) -> SecurityScanResult:
        """Call the internal DLP/PII scanner for one article."""

        payload = {
            "article_number": article.article_number,
            "text": article.text,
            "metadata": article.metadata,
            "classification": article.classification.classification.value,
            "source_hash": article.source_hash,
        }
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=20.0,
            transport=self._http_transport,
        ) as client:
            response = await client.post("/scan", json=payload)
            response.raise_for_status()
        body: dict[str, Any] = response.json()
        return SecurityScanResult.model_validate(body)


class SamaAuditor:
    """Apply internal security gate decisions and index allowed articles."""

    def __init__(
        self,
        *,
        security_gate: SecurityGate | None = None,
        vector_indexer: VectorIndexer,
        text_indexer: TextIndexer,
        object_store: ObjectStore,
        quarantine_bucket: str | None = None,
        audit: QalaAuditAdapter | None = None,
        tenant_id: str = "sama-ingestion",
    ) -> None:
        self._security_gate = security_gate or HttpSecurityGate()
        self._vector_indexer = vector_indexer
        self._text_indexer = text_indexer
        self._object_store = object_store
        self._quarantine_bucket = quarantine_bucket or os.environ.get(
            "SAMA_QUARANTINE_BUCKET",
            "sama-quarantine",
        )
        self._audit = audit
        self._tenant_id = tenant_id

    async def audit_parse_result(
        self,
        parse_result: ParseResult,
        *,
        trace_id: str | None = None,
    ) -> tuple[AuditDecision, ...]:
        """Audit and index/quarantine every article in a parse result."""

        effective_trace_id = trace_id or str(uuid.uuid4())
        decisions: list[AuditDecision] = []
        for article in parse_result.articles:
            decisions.append(await self.audit_article(article, trace_id=effective_trace_id))
        return tuple(decisions)

    async def audit_article(
        self,
        article: ParsedArticle,
        *,
        trace_id: str | None = None,
    ) -> AuditDecision:
        """Audit one article and perform the resulting storage/indexing action."""

        effective_trace_id = trace_id or str(uuid.uuid4())
        scan = await self._security_gate.scan(article)
        ticket_key: str | None = None
        indexed = False
        if scan.verdict == "ALLOW":
            await self._vector_indexer.upsert_article(article)
            await self._text_indexer.index_article(article)
            indexed = True
        elif scan.verdict == "QUARANTINE":
            ticket_key = await self._create_review_ticket(article, scan)
        elif scan.verdict == "BLOCK":
            indexed = False
        else:  # pragma: no cover - guarded by Pydantic Literal validation
            raise ValueError(f"unsupported security gate verdict: {scan.verdict}")

        decision = AuditDecision(
            article_number=article.article_number,
            source_hash=article.source_hash,
            verdict=scan.verdict,
            indexed=indexed,
            quarantine_ticket_key=ticket_key,
        )
        record_audit_event(
            action="sama_audit_decision",
            trace_id=effective_trace_id,
            tenant_id=self._tenant_id,
            audit=self._audit,
            payload={
                "article_number": article.article_number,
                "source_hash": article.source_hash,
                "verdict": scan.verdict,
                "indexed": indexed,
                "quarantine_ticket_key": ticket_key,
                "reasons": list(scan.reasons),
                "message_ar": "تم تطبيق قرار بوابة الأمن على مادة SAMA قبل الفهرسة.",
            },
        )
        return decision

    async def _create_review_ticket(
        self,
        article: ParsedArticle,
        scan: SecurityScanResult,
    ) -> str:
        ticket_key = f"tickets/{article.source_hash}-{article.article_number or 'document'}.json"
        ticket: Mapping[str, object] = {
            "article_number": article.article_number,
            "source_hash": article.source_hash,
            "classification": article.classification.classification.value,
            "reasons": list(scan.reasons),
            "text_preview": article.text[:500],
        }
        await self._object_store.put_object(
            self._quarantine_bucket,
            ticket_key,
            json.dumps(ticket, ensure_ascii=False).encode("utf-8"),
            "application/json",
        )
        return ticket_key
