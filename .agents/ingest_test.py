# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
POC — ADR-0001 Sanctioned Exception
====================================
This file is a proof-of-concept granted by operator decision on 2026-05-16.
See docs/decisions/ADR-0001-swarms-boundary.md for the boundary it temporarily
crosses (RAG pipeline inside .agents/). A follow-up issue tracks the ADR
revision needed before this pattern is promoted to production.

Ingests PDPL Article 22 (Cross-Border Data Transfer) into the Modal-sovereign
Qdrant instance (qarar-rag-infra, Qdrant 1.12.6). Embeddings use BAAI/bge-m3
via FlagEmbedding. All data remains sovereign: no Qdrant Cloud, no external
vector stores.

Deployment:
    modal deploy .agents/ingest_test.py

Endpoints (after deploy — copy URLs into secrets, never commit them):
    POST <INGEST_ENDPOINT>  label=pdpl-ingest  — runs ingestion
    POST <VERIFY_ENDPOINT>  label=pdpl-verify  — similarity search probe

Required Modal secrets:
    huggingface-secret   → HF_TOKEN             (bge-m3 model download)
    qdrant-infra-secret  → QDRANT_INTERNAL_URL   (Modal-sovereign Qdrant URL)
                           QDRANT_API_KEY         (required unless break-glass
                                                   ALLOW_UNAUTHENTICATED_QDRANT=true)
    agent-api-secret     → AGENT_API_TOKEN        (shared Bearer auth, same as curlexai-agents)

Smoke test (requires Modal auth):
    modal run .agents/ingest_test.py
"""

from __future__ import annotations

import hmac
import os
import re
import sys as _sys
from pathlib import Path as _Path
from typing import Optional

import modal
from fastapi import Body, Header, HTTPException

# `.agents` is not an importable package (leading dot), so resolve the sibling
# runtime_security module by absolute path. Modal automounts locally-imported
# modules, so this also ships runtime_security.py into the containers.
_AGENTS_DIR = str(_Path(__file__).resolve().parent)
if _AGENTS_DIR not in _sys.path:
    _sys.path.insert(0, _AGENTS_DIR)

from runtime_security import require_qdrant_auth  # noqa: E402

# ── Modal app (separate from curlexai-agents) ────────────────────────────────

app = modal.App("curlexai-rag-test")

ingest_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "FlagEmbedding>=1.2,<2.0",
        "qdrant-client>=1.9,<2.0",
    )
)

hf_secret = modal.Secret.from_name("huggingface-secret")
qdrant_secret = modal.Secret.from_name("qdrant-infra-secret")
api_secret = modal.Secret.from_name("agent-api-secret")

# ── Constants ────────────────────────────────────────────────────────────────

COLLECTION_NAME = "qarar_regulatory_test"
VECTOR_DIM = 1024          # bge-m3 dense embedding output dimension
BGE_MODEL_ID = "BAAI/bge-m3"

# PDPL Article 22 — نقل البيانات الشخصية خارج المملكة
# Source: Saudi Personal Data Protection Law (Royal Decree M/19, 1443H / 2021).
# Structured into 4 natural segments: preamble + three conditions.
# Verify the exact wording against the official SDAIA publication before
# any production use.
PDPL_ARTICLE_22: str = (
    "المادة الثانية والعشرون: نقل البيانات الشخصية خارج المملكة. "
    "لا يجوز نقل البيانات الشخصية إلى جهة خارج المملكة أو الإفصاح عنها لها "
    "أو إتاحة الاطلاع عليها إلا وفقاً للضوابط والإجراءات التي تحددها اللائحة، "
    "وبما يحقق مستوى مناسباً من الحماية على النحو المحدد في هذا النظام، "
    "وبعد التحقق من الشروط الآتية. "
    "أولاً: ألا يخل النقل بالأمن الوطني أو يضر بالمصلحة الوطنية، ويشترط "
    "ألا يكون للنقل أثر سلبي على المملكة أو على القطاعات الحيوية فيها. "
    "ثانياً: ألا يؤدي النقل إلى انتهاك خصوصية صاحب البيانات الشخصية أو "
    "تعريضها للخطر، ويجب على المتحكم التحقق من أن الجهة المستلمة خارج المملكة "
    "تلتزم بمعايير حماية البيانات المعتمدة ولديها ضمانات كافية لحماية البيانات. "
    "ثالثاً: أن يكون الغرض من النقل مشروعاً ومتوافقاً مع الغرض الذي جُمعت "
    "من أجله البيانات، وأن تتوافر لدى الجهة المستلمة خارج المملكة الضمانات "
    "الكافية لحماية البيانات الشخصية بما يتناسب مع طبيعتها وحجمها ودرجة حساسيتها."
)

# ── Pure utility functions ───────────────────────────────────────────────────

def sentence_chunk(text: str) -> list[str]:
    """
    Split Article 22 on Arabic ordinal markers into 3–4 segments.
    Returns [preamble, condition_1, condition_2, condition_3].
    """
    ordinal_re = re.compile(
        r"(?=(?:أولاً|ثانياً|ثالثاً|رابعاً|خامساً)[:：])"
    )
    parts = ordinal_re.split(text)
    preamble = parts[0].strip()
    conditions = [p.strip() for p in parts[1:] if p.strip()]
    return [preamble] + conditions


def _chunk_point_id(chunk_index: int) -> int:
    """Stable positive integer ID per chunk so re-runs overwrite existing points."""
    return chunk_index + 1


def _qdrant_client():  # type: ignore[return]  # qdrant_client not available at import time
    from qdrant_client import QdrantClient

    require_qdrant_auth()
    url = os.environ["QDRANT_INTERNAL_URL"]
    api_key: Optional[str] = os.environ.get("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)


def _verify_bearer_token(authorization: Optional[str]) -> None:
    expected = os.environ.get("AGENT_API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="agent_api_token_missing")
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")
    # HTTP auth scheme is case-insensitive (RFC 7235) — matches modal_app.py pattern
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid_token")


# ── Ingestor class (holds bge-m3 warm across calls) ─────────────────────────

@app.cls(
    image=ingest_image,
    secrets=[hf_secret, qdrant_secret, api_secret],
    timeout=300,
    max_containers=1,
    min_containers=0,
)
class PDPLIngestor:
    @modal.enter()
    def load_model(self) -> None:
        from FlagEmbedding import BGEM3FlagModel  # noqa: PLC0415

        self.model = BGEM3FlagModel(BGE_MODEL_ID, use_fp16=False)

    @modal.method()
    def ingest(self) -> dict:
        from qdrant_client.models import Distance, PointStruct, VectorParams  # noqa: PLC0415

        chunks = sentence_chunk(PDPL_ARTICLE_22)
        encoded = self.model.encode(
            chunks,
            batch_size=len(chunks),
            max_length=512,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        vectors: list[list[float]] = [v.tolist() for v in encoded["dense_vecs"]]

        client = _qdrant_client()
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )

        points = [
            PointStruct(
                id=_chunk_point_id(i),
                vector=vectors[i],
                payload={
                    "text": chunk,
                    "article": "PDPL-22",
                    "chunk_index": i,
                    "source": "PDPL-2021",
                    "jurisdiction": "SA",
                },
            )
            for i, chunk in enumerate(chunks)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        return {
            "status": "ok",
            "collection": COLLECTION_NAME,
            "chunks_ingested": len(points),
        }

    @modal.method()
    def verify(self, query: str) -> dict:
        client = _qdrant_client()
        if not client.collection_exists(COLLECTION_NAME):
            return {
                "query": query,
                "hits": [],
                "error": "collection not found — run ingest first",
            }

        encoded = self.model.encode(
            [query],
            batch_size=1,
            max_length=512,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        vector: list[float] = encoded["dense_vecs"][0].tolist()

        result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=3,
        )
        return {
            "query": query,
            "hits": [
                {
                    "score": round(float(h.score), 4),
                    "chunk_index": (h.payload or {}).get("chunk_index"),
                    "text": (h.payload or {}).get("text", "")[:200],
                }
                for h in result.points
            ],
        }


# ── Web endpoints ────────────────────────────────────────────────────────────

@app.function(
    image=ingest_image,
    secrets=[hf_secret, qdrant_secret, api_secret],
    timeout=300,
    min_containers=0,
)
@modal.fastapi_endpoint(method="POST", label="pdpl-ingest")
def ingest_web(
    authorization: str | None = Header(default=None),
    payload: dict = Body(default={}),
) -> dict:
    _verify_bearer_token(authorization)
    ingestor = PDPLIngestor()
    return ingestor.ingest.remote()


@app.function(
    image=ingest_image,
    secrets=[hf_secret, qdrant_secret, api_secret],
    timeout=120,
    min_containers=0,
)
@modal.fastapi_endpoint(method="POST", label="pdpl-verify")
def verify_web(
    authorization: str | None = Header(default=None),
    payload: dict = Body(default={}),
) -> dict:
    _verify_bearer_token(authorization)
    query: str = payload.get("query", "نقل البيانات الشخصية")
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(status_code=400, detail="'query' must be a non-empty string")
    ingestor = PDPLIngestor()
    return ingestor.verify.remote(query)


# ── Smoke test (modal run .agents/ingest_test.py) ────────────────────────────

@app.local_entrypoint()
def test() -> None:
    print("=== Smoke test: PDPL Article 22 ingestion ===")
    ingestor = PDPLIngestor()

    ingest_result = ingestor.ingest.remote()
    print(f"Ingest: {ingest_result}")

    # Known phrase from Article 22 — must surface chunk_index=0 (preamble) or 1 (أولاً)
    verify_result = ingestor.verify.remote("نقل البيانات الشخصية خارج المملكة")
    print("Verify hits:")
    for hit in verify_result["hits"]:
        print(f"  [{hit['score']}] chunk {hit['chunk_index']}: {hit['text'][:80]}...")
