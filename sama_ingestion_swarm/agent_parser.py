# SPDX-License-Identifier: MIT
# Licensed under MIT
"""SAMA parser agent for sovereign regulatory documents."""

from __future__ import annotations

import io
import json
import re
import uuid
from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel, Field

from sama_ingestion_swarm import record_audit_event
from sama_ingestion_swarm.agent_fetcher import FetchResult
from src.core.audited_router import QalaAuditAdapter
from src.core.classification import ClassificationDecision, classify_content


class ObjectStore(Protocol):
    """Async object-store port used by the parser."""

    async def get_object(self, bucket: str, key: str) -> bytes:
        """Read object bytes from storage."""

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Write object bytes to storage."""


class ParsedArticle(BaseModel):
    """Structured SAMA article extracted from a source artifact."""

    article_number: str | None = None
    text: str = Field(min_length=1)
    metadata: dict[str, object]
    classification: ClassificationDecision
    source_hash: str = Field(min_length=64, max_length=64)


class ParseResult(BaseModel):
    """Parser output for one source artifact."""

    source_hash: str = Field(min_length=64, max_length=64)
    source_url: str = Field(min_length=1)
    articles: tuple[ParsedArticle, ...]
    bucket: str = Field(min_length=1)
    object_key: str = Field(min_length=1)


_ARTICLE_RE = re.compile(
    r"(?:^|[\n.])\s*(?:المادة|مادة|الماده|ماده)\s*(?:\(?\s*([\d٠-٩]+|[اأإآء-ي]+)\s*\)?)\s*[:：\-–]?\s*",
    re.MULTILINE,
)
_ALEF_VARIANTS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه"})


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text for article splitting and downstream indexing."""

    normalized = text.translate(_ALEF_VARIANTS).replace("ـ", "")
    return re.sub(r"[ \t\r\f\v]+", " ", normalized).strip()


def split_articles(text: str) -> tuple[tuple[str | None, str], ...]:
    """Split Arabic legal/regulatory text into article-like chunks."""

    matches = list(_ARTICLE_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        return ((None, stripped),) if stripped else ()

    articles: list[tuple[str | None, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            articles.append((match.group(1), body))
    return tuple(articles)


def _extract_html_text(content: bytes) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(content, "html.parser")
    return str(soup.get_text("\n", strip=True))


def _extract_pdf_text(content: bytes) -> str:
    import pdfplumber
    text_parts: list[str] = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def extract_text(content: bytes, content_type: str, object_key: str) -> str:
    """Extract text from a SAMA HTML or PDF artifact."""

    if content_type == "application/pdf" or object_key.lower().endswith(".pdf"):
        return _extract_pdf_text(content)
    return _extract_html_text(content)


class SamaParser:
    """Parse raw SAMA artifacts into classified structured articles."""

    def __init__(
        self,
        *,
        object_store: ObjectStore,
        parsed_bucket: str = "sama-parsed",
        audit: QalaAuditAdapter | None = None,
        tenant_id: str = "sama-ingestion",
    ) -> None:
        self._object_store = object_store
        self._parsed_bucket = parsed_bucket
        self._audit = audit
        self._tenant_id = tenant_id

    async def parse_fetch_result(
        self,
        fetch_result: FetchResult,
        *,
        trace_id: str | None = None,
    ) -> ParseResult:
        """Parse one fetched SAMA artifact and write structured JSON output."""

        effective_trace_id = trace_id or str(uuid.uuid4())
        raw = await self._object_store.get_object(fetch_result.bucket, fetch_result.object_key)
        extracted = extract_text(raw, fetch_result.content_type, fetch_result.object_key)
        normalized = normalize_arabic(extracted)
        chunks = split_articles(normalized)
        articles: list[ParsedArticle] = []
        for article_number, article_text in chunks:
            metadata: dict[str, object] = {
                "source_url": fetch_result.source_url,
                "object_key": fetch_result.object_key,
                "content_type": fetch_result.content_type,
            }
            decision = classify_content(fetch_result.source_url, article_text[:4000], metadata)
            articles.append(
                ParsedArticle(
                    article_number=article_number,
                    text=article_text,
                    metadata=metadata,
                    classification=decision,
                    source_hash=fetch_result.sha256,
                )
            )

        parse_result = ParseResult(
            source_hash=fetch_result.sha256,
            source_url=fetch_result.source_url,
            articles=tuple(articles),
            bucket=self._parsed_bucket,
            object_key=f"parsed/{fetch_result.sha256}.json",
        )
        await self._object_store.put_object(
            self._parsed_bucket,
            parse_result.object_key,
            json.dumps(parse_result.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"),
            "application/json",
        )
        record_audit_event(
            action="sama_parse",
            trace_id=effective_trace_id,
            tenant_id=self._tenant_id,
            audit=self._audit,
            payload={
                "source_hash": fetch_result.sha256,
                "article_count": len(articles),
                "classifications": [a.classification.classification.value for a in articles],
                "message_ar": "تم تحليل وثيقة SAMA وتصنيف موادها داخل البيئة السيادية.",
            },
        )
        return parse_result

    @staticmethod
    def articles_as_jsonable(parse_result: ParseResult) -> list[Mapping[str, object]]:
        """Return parser articles as JSON-compatible dictionaries."""

        return [article.model_dump(mode="json") for article in parse_result.articles]
