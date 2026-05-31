# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Orchestrator for the SAMA ingestion swarm pipeline."""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Sequence

from pydantic import BaseModel, Field

from sama_ingestion_swarm import record_audit_event
from sama_ingestion_swarm.agent_auditor import AuditDecision, SamaAuditor
from sama_ingestion_swarm.agent_fetcher import FetchResult, SamaFetcher
from sama_ingestion_swarm.agent_parser import ParseResult, SamaParser
from src.core.audited_router import QalaAuditAdapter

DEFAULT_PIPELINE_INTERVAL_SECONDS = 6 * 60 * 60


class PipelineDocumentResult(BaseModel):
    """Pipeline result for one requested SAMA source URL."""

    source_url: str = Field(min_length=1)
    fetched: FetchResult | None = None
    parsed: ParseResult | None = None
    audit_decisions: tuple[AuditDecision, ...] = ()
    errors: tuple[str, ...] = ()


class PipelineRunResult(BaseModel):
    """Pipeline run summary."""

    trace_id: str = Field(min_length=1)
    documents: tuple[PipelineDocumentResult, ...]


class SamaIngestionOrchestrator:
    """Coordinate fetch, parse, and audit agents with per-document isolation."""

    def __init__(
        self,
        *,
        fetcher: SamaFetcher,
        parser: SamaParser,
        auditor: SamaAuditor,
        interval_seconds: int | None = None,
        audit: QalaAuditAdapter | None = None,
        tenant_id: str = "sama-ingestion",
    ) -> None:
        self._fetcher = fetcher
        self._parser = parser
        self._auditor = auditor
        self._interval_seconds = interval_seconds or int(
            os.environ.get("SAMA_PIPELINE_INTERVAL_SECONDS", str(DEFAULT_PIPELINE_INTERVAL_SECONDS))
        )
        self._audit = audit
        self._tenant_id = tenant_id

    @property
    def interval_seconds(self) -> int:
        """Return the configured scheduler interval."""

        return self._interval_seconds

    async def run_once(self, urls: Sequence[str]) -> PipelineRunResult:
        """Run the full SAMA ingestion pipeline once."""

        trace_id = str(uuid.uuid4())
        record_audit_event(
            action="pipeline_start",
            trace_id=trace_id,
            tenant_id=self._tenant_id,
            audit=self._audit,
            payload={
                "document_count": len(urls),
                "message_ar": "بدأ تشغيل خط معالجة وثائق SAMA داخل البيئة السيادية.",
            },
        )
        results: list[PipelineDocumentResult] = []
        for url in urls:
            results.append(await self._process_document(url, trace_id=trace_id))
        record_audit_event(
            action="pipeline_complete",
            trace_id=trace_id,
            tenant_id=self._tenant_id,
            audit=self._audit,
            payload={
                "document_count": len(results),
                "error_count": sum(len(result.errors) for result in results),
                "message_ar": "اكتمل تشغيل خط معالجة وثائق SAMA مع عزل أخطاء كل وثيقة.",
            },
        )
        return PipelineRunResult(trace_id=trace_id, documents=tuple(results))

    async def run_schedule(
        self,
        urls: Sequence[str],
        *,
        max_iterations: int | None = None,
    ) -> list[PipelineRunResult]:
        """Run the pipeline on a configurable async schedule."""

        runs: list[PipelineRunResult] = []
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            runs.append(await self.run_once(urls))
            iteration += 1
            if max_iterations is not None and iteration >= max_iterations:
                break
            await asyncio.sleep(self._interval_seconds)
        return runs

    async def _process_document(self, url: str, *, trace_id: str) -> PipelineDocumentResult:
        errors: list[str] = []
        fetched: FetchResult | None = None
        parsed: ParseResult | None = None
        decisions: tuple[AuditDecision, ...] = ()
        try:
            fetched = await self._fetcher.fetch_one(url, trace_id=trace_id)
        except Exception as exc:
            errors.append(f"fetch_failed:{exc.__class__.__name__}")
            return PipelineDocumentResult(source_url=url, errors=tuple(errors))

        try:
            parsed = await self._parser.parse_fetch_result(fetched, trace_id=trace_id)
        except Exception as exc:
            errors.append(f"parse_failed:{exc.__class__.__name__}")
            return PipelineDocumentResult(source_url=url, fetched=fetched, errors=tuple(errors))

        try:
            decisions = await self._auditor.audit_parse_result(parsed, trace_id=trace_id)
        except Exception as exc:
            errors.append(f"audit_failed:{exc.__class__.__name__}")

        return PipelineDocumentResult(
            source_url=url,
            fetched=fetched,
            parsed=parsed,
            audit_decisions=decisions,
            errors=tuple(errors),
        )
