# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx
import modal
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

QDRANT_PORT = 6333
QDRANT_URL = f"http://127.0.0.1:{QDRANT_PORT}"
LOCAL_STORAGE = Path("/qdrant/storage")
SNAPSHOT_DIR = Path("/snapshots")
COLLECTION_NAME = "qarar_regulatory"

volume = modal.Volume.from_name("qarar-qdrant-snapshots", create_if_missing=True)
image = (
    modal.Image.from_registry("qdrant/qdrant:v1.15.3", add_python="3.12")
    .pip_install("fastapi", "httpx", "pydantic")
)
app = modal.App("qarar-rag-infra", image=image)


class IngestDoc(BaseModel):
    doc_id: str = Field(min_length=3, max_length=128)
    text: str = Field(min_length=1, max_length=100_000)
    source: str = Field(min_length=1, max_length=512)
    authority: str = Field(min_length=1, max_length=128)
    article: str | None = None
    section: str | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4_000)
    top_k: int = Field(default=5, ge=1, le=20)


def _safe_log(event_type: str, payload: dict[str, Any]) -> None:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if "secret" in lowered or "token" in lowered or "key" in lowered or "password" in lowered:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    print(json.dumps({"event_type": event_type, "payload": redacted, "ts": int(time.time())}))


def verify_hmac(raw_body: bytes, timestamp: str, signature: str, secret: str) -> None:
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid timestamp") from exc

    now = int(time.time())
    if abs(now - ts) > 300:
        raise HTTPException(status_code=401, detail="Expired request")

    payload = timestamp.encode("utf-8") + b"." + raw_body
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


def reject_secret_like_text(text: str) -> None:
    secret_markers = [
        "sk-",
        "sk-proj-",
        "sk-admin-",
        "sk-ant-",
        "ghp_",
        "github_pat_",
        "AIza",
        "xai-",
        "gsk_",
        "pplx-",
        "BEGIN PRIVATE KEY",
        "RENDER_DEPLOY_HOOK",
        "TELEGRAM_BOT_TOKEN",
    ]
    lowered = text.lower()
    for marker in secret_markers:
        if marker.lower() in lowered:
            raise HTTPException(status_code=400, detail="Payload appears to contain secrets")


@app.cls(
    volumes={"/snapshots": volume},
    min_containers=1,
    max_containers=1,
    timeout=24 * 60 * 60,
    secrets=[modal.Secret.from_name("qarar-rag-secrets")],
)
class QararRAGInfra:
    @modal.enter()
    def start(self) -> None:
        self.hmac_secret = os.environ["QARAR_RAG_HMAC_SECRET"]
        self.qdrant_api_key = os.environ["QDRANT_API_KEY"]
        LOCAL_STORAGE.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.proc = subprocess.Popen(
            [
                "/qdrant/qdrant",
                "--storage-dir",
                str(LOCAL_STORAGE),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        self._wait_for_qdrant()
        self._ensure_collection_exists()
        _safe_log("qarar_rag_started", {"collection": COLLECTION_NAME})

    def _wait_for_qdrant(self) -> None:
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                response = httpx.get(f"{QDRANT_URL}/healthz", timeout=2)
                if response.status_code < 500:
                    return
            except httpx.HTTPError:
                time.sleep(1)
        raise RuntimeError("Qdrant did not become healthy")

    def _ensure_collection_exists(self) -> None:
        response = httpx.get(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}",
            headers={"api-key": self.qdrant_api_key},
            timeout=10,
        )
        if response.status_code == 200:
            return
        if response.status_code != 404:
            raise RuntimeError(f"Qdrant collection check failed: {response.status_code}")

        create_payload = {
            "vectors": {
                "dense": {
                    "size": 1024,
                    "distance": "Cosine",
                }
            }
        }
        create_response = httpx.put(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}",
            headers={"api-key": self.qdrant_api_key},
            json=create_payload,
            timeout=30,
        )
        if create_response.status_code >= 400:
            raise RuntimeError(f"Qdrant collection creation failed: {create_response.text}")

    async def _verify_request(self, request: Request, timestamp: str, signature: str) -> bytes:
        raw_body = await request.body()
        verify_hmac(raw_body, timestamp, signature, self.hmac_secret)
        return raw_body

    def _persist_snapshot(self, snapshot_payload: dict[str, Any]) -> str:
        result = snapshot_payload.get("result", {})
        name = result.get("name") if isinstance(result, dict) else None
        if not isinstance(name, str) or not name:
            raise HTTPException(status_code=500, detail="Snapshot name missing")

        response = httpx.get(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/snapshots/{name}",
            headers={"api-key": self.qdrant_api_key},
            timeout=120,
        )
        if response.status_code >= 400:
            _safe_log("snapshot_download_failed", {"status": response.status_code})
            raise HTTPException(status_code=500, detail="Snapshot download failed")

        target = SNAPSHOT_DIR / name
        target.write_bytes(response.content)
        volume.commit()
        return name

    @modal.asgi_app()
    def api(self):
        web = FastAPI(title="Qarar RAG Infra", version="1.0.0")

        @web.get("/health")
        def health():
            try:
                response = httpx.get(f"{QDRANT_URL}/healthz", timeout=2)
                return {
                    "ok": response.status_code < 500,
                    "qdrant_status": response.status_code,
                    "collection": COLLECTION_NAME,
                }
            except httpx.HTTPError:
                return {"ok": False, "collection": COLLECTION_NAME}

        @web.post("/ingest")
        async def ingest(
            request: Request,
            x_qarar_timestamp: str = Header(...),
            x_qarar_signature: str = Header(...),
        ):
            raw_body = await self._verify_request(request, x_qarar_timestamp, x_qarar_signature)
            docs_json = json.loads(raw_body.decode("utf-8"))
            docs = [IngestDoc.model_validate(item) for item in docs_json]
            for doc in docs:
                reject_secret_like_text(doc.text)
            _safe_log("ingest_accepted", {"count": len(docs), "collection": COLLECTION_NAME})
            return {
                "ok": True,
                "accepted": len(docs),
                "note": "Embedding worker integration is intentionally separate.",
            }

        @web.post("/search")
        async def search(
            request: Request,
            x_qarar_timestamp: str = Header(...),
            x_qarar_signature: str = Header(...),
        ):
            raw_body = await self._verify_request(request, x_qarar_timestamp, x_qarar_signature)
            req = SearchRequest.model_validate_json(raw_body)
            reject_secret_like_text(req.query)
            _safe_log("search_accepted", {"top_k": req.top_k, "collection": COLLECTION_NAME})
            return {
                "ok": True,
                "results": [],
                "note": "Vector embedding integration must populate query vector before Qdrant search.",
            }

        @web.post("/snapshot")
        async def snapshot(
            request: Request,
            x_qarar_timestamp: str = Header(...),
            x_qarar_signature: str = Header(...),
        ):
            await self._verify_request(request, x_qarar_timestamp, x_qarar_signature)
            response = httpx.post(
                f"{QDRANT_URL}/collections/{COLLECTION_NAME}/snapshots",
                headers={"api-key": self.qdrant_api_key},
                timeout=120,
            )
            if response.status_code >= 400:
                _safe_log("snapshot_failed", {"status": response.status_code})
                raise HTTPException(status_code=500, detail="Snapshot failed")

            payload = response.json()
            snapshot_name = self._persist_snapshot(payload)
            _safe_log("snapshot_created", {"collection": COLLECTION_NAME, "snapshot": snapshot_name})
            return {"ok": True, "snapshot": snapshot_name}

        return web

    @modal.exit()
    def stop(self) -> None:
        try:
            volume.commit()
            _safe_log("volume_committed", {"path": str(SNAPSHOT_DIR)})
        finally:
            self.proc.terminate()
