"""SAMA fetcher agent for sovereign regulatory ingestion."""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from collections.abc import Sequence
from typing import Protocol
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from sama_ingestion_swarm import record_audit_event
from src.core.audited_router import QalaAuditAdapter

DEFAULT_FETCH_INTERVAL_SECONDS = 6 * 60 * 60


class ObjectStore(Protocol):
    """Async object-store port used by the SAMA fetcher."""

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Store an object in the configured bucket."""


class MinioObjectStore:
    """MinIO object-store adapter configured from environment variables.

    Required environment variables:
        ``MINIO_ENDPOINT``, ``MINIO_ACCESS_KEY``, ``MINIO_SECRET_KEY``.
    Optional environment variables:
        ``MINIO_SECURE`` (default: ``true``).
    """

    def __init__(self) -> None:
        from minio import Minio

        endpoint = os.environ.get("MINIO_ENDPOINT", "")
        access_key = os.environ.get("MINIO_ACCESS_KEY", "")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "")
        secure = os.environ.get("MINIO_SECURE", "true").lower() != "false"
        if not endpoint or not access_key or not secret_key:
            raise ValueError("MINIO_ENDPOINT, MINIO_ACCESS_KEY, and MINIO_SECRET_KEY are required")
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Store an object in MinIO, creating the bucket when absent."""

        from io import BytesIO

        def _write() -> None:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
            self._client.put_object(
                bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

        await asyncio.to_thread(_write)

    async def get_object(self, bucket: str, key: str) -> bytes:
        """Read an object from MinIO."""

        def _read() -> bytes:
            response = self._client.get_object(bucket, key)
            try:
                return bytes(response.read())
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_read)


class FetchResult(BaseModel):
    """Raw SAMA artifact fetch result."""

    source_url: str = Field(min_length=1)
    bucket: str = Field(min_length=1)
    object_key: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)
    content_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)


class SamaFetcher:
    """Fetch SAMA regulatory artifacts into sovereign object storage."""

    def __init__(
        self,
        *,
        object_store: ObjectStore | None = None,
        bucket: str | None = None,
        allowed_domains: Sequence[str] | None = None,
        interval_seconds: int | None = None,
        audit: QalaAuditAdapter | None = None,
        tenant_id: str = "sama-ingestion",
        http_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._object_store = object_store or MinioObjectStore()
        self._bucket = bucket or os.environ.get("SAMA_RAW_BUCKET", "sama-raw")
        configured_domains = os.environ.get("SAMA_ALLOWED_DOMAINS", "www.sama.gov.sa,sama.gov.sa")
        domains = allowed_domains or tuple(host.strip() for host in configured_domains.split(","))
        self._allowed_domains = frozenset(host.lower() for host in domains if host.strip())
        self._interval_seconds = interval_seconds or int(
            os.environ.get("SAMA_FETCH_INTERVAL_SECONDS", str(DEFAULT_FETCH_INTERVAL_SECONDS))
        )
        self._audit = audit
        self._tenant_id = tenant_id
        self._http_transport = http_transport

    @property
    def interval_seconds(self) -> int:
        """Return the configured scheduler interval."""

        return self._interval_seconds

    def validate_source_url(self, url: str) -> str:
        """Validate that a source URL is HTTPS and SAMA-allowlisted."""

        parsed = urlparse(url)
        host = parsed.hostname.lower() if parsed.hostname else ""
        if parsed.scheme != "https" or host not in self._allowed_domains:
            raise ValueError("SAMA source URL must be HTTPS and domain-allowlisted")
        return url

    async def fetch_one(self, url: str, *, trace_id: str | None = None) -> FetchResult:
        """Fetch one SAMA artifact and persist it to object storage."""

        source_url = self.validate_source_url(url)
        effective_trace_id = trace_id or str(uuid.uuid4())
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=30.0,
            transport=self._http_transport,
        ) as client:
            response = await client.get(source_url)
            if 300 <= response.status_code < 400:
                location = response.headers.get("location", "")
                self.validate_source_url(str(httpx.URL(source_url).join(location)))
                raise ValueError("redirects are not followed during sovereign SAMA fetches")
            response.raise_for_status()

        content = response.content
        artifact_hash = hashlib.sha256(content).hexdigest()
        content_type = response.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
        suffix = ".pdf" if content_type == "application/pdf" or source_url.lower().endswith(".pdf") else ".html"
        object_key = f"raw/{artifact_hash}{suffix}"
        await self._object_store.put_object(self._bucket, object_key, content, content_type)
        result = FetchResult(
            source_url=source_url,
            bucket=self._bucket,
            object_key=object_key,
            sha256=artifact_hash,
            content_type=content_type,
            size_bytes=len(content),
        )
        record_audit_event(
            action="sama_fetch",
            trace_id=effective_trace_id,
            tenant_id=self._tenant_id,
            audit=self._audit,
            payload={
                "source_url": source_url,
                "bucket": self._bucket,
                "object_key": object_key,
                "sha256": artifact_hash,
                "size_bytes": len(content),
                "message_ar": "تم جلب وثيقة من مصدر SAMA مسموح وتخزينها في المستودع السيادي.",
            },
        )
        return result

    async def run_schedule(
        self,
        urls: Sequence[str],
        *,
        max_iterations: int | None = None,
    ) -> list[FetchResult]:
        """Run a testable async fetch schedule."""

        results: list[FetchResult] = []
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            trace_id = str(uuid.uuid4())
            for url in urls:
                results.append(await self.fetch_one(url, trace_id=trace_id))
            iteration += 1
            if max_iterations is not None and iteration >= max_iterations:
                break
            await asyncio.sleep(self._interval_seconds)
        return results
