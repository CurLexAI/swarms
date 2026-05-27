# SPDX-License-Identifier: MIT
# Licensed under MIT
"""ADR-0005-pending stub. See .agents/gateway/README.md.

This module is a deliberately inert OpenAI-compatible shim. It exposes
the *shape* of a gateway so ADR-0005 reviewers can see what would be
involved, without performing any Modal call, embedding any endpoint
URL, or enabling client tools to reach Mihwar or Bayyinah.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

ADR_REFERENCE = "docs/decisions/ADR-0005-public-llm-gateway.md"
ACK_ENV = "SWARMS_GATEWAY_STUB_ACK"


def _refuse() -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "error": (
                "ADR-0005 has not been accepted. "
                "This stub does not proxy Modal."
            ),
            "adr": ADR_REFERENCE,
        },
    )


def create_app() -> FastAPI:
    if os.environ.get(ACK_ENV) != "1":
        raise RuntimeError(
            f"Refusing to start gateway stub: set {ACK_ENV}=1 after "
            f"reading .agents/gateway/README.md."
        )

    app = FastAPI(
        title="swarms-gateway-stub",
        description=(
            "ADR-0005-pending scaffolding. Not a production gateway. "
            "All model endpoints return 501."
        ),
        version="0.0.0-stub",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {"status": "stub", "adr": ADR_REFERENCE}

    @app.post("/v1/chat/completions")
    def chat_completions() -> JSONResponse:
        return _refuse()

    @app.post("/v1/completions")
    def completions() -> JSONResponse:
        return _refuse()

    @app.get("/v1/models")
    def models() -> JSONResponse:
        return _refuse()

    return app


app: FastAPI | None
try:
    app = create_app()
except RuntimeError:
    app = None
