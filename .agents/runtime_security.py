# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
Runtime security primitives for the Modal agent runtime.
=========================================================
Fail-closed helpers shared by `.agents/modal_app.py` and `.agents/ingest_test.py`:

* `require_pinned_revision` / `trust_remote_code_for` — supply-chain guard that
  refuses to load a model from a mutable ref or to execute remote model code
  unless a pinned commit SHA AND a deliberate acknowledgement are both present.
* `verify_bearer_token` — endpoint-specific Bearer auth (no shared token by
  default; an explicit break-glass flag re-enables the legacy shared token).
* `require_qdrant_auth` — Qdrant must be authenticated unless an explicit
  break-glass flag is set for an isolated, network-protected lab instance.

These helpers are intentionally dependency-light: `fastapi` is imported lazily
inside `verify_bearer_token` so the model-loading path (which runs inside the
GPU container) can import the revision/Qdrant guards without pulling in fastapi.
"""

from __future__ import annotations

import hmac
import os
import re
from dataclasses import dataclass
from typing import Final

FULL_COMMIT_SHA: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
REMOTE_CODE_ACK: Final[str] = "ALLOW_PINNED_REVIEWED_REMOTE_CODE"


@dataclass(frozen=True)
class ModelPolicy:
    model_id: str
    revision_env: str
    remote_code_ack_env: str


def require_pinned_revision(env_name: str) -> str:
    revision = os.environ.get(env_name, "").strip()
    if not revision:
        raise RuntimeError(f"{env_name}_missing")
    if not FULL_COMMIT_SHA.fullmatch(revision):
        raise RuntimeError(f"{env_name}_must_be_full_40_char_commit_sha")
    return revision


def trust_remote_code_for(policy: ModelPolicy) -> bool:
    """
    Fail-closed model loading policy.

    Remote code is disabled unless:
    1. model revision is pinned to a full commit SHA; and
    2. a deliberate acknowledgement env var is set.

    This prevents accidental supply-chain execution from mutable model refs.
    """
    require_pinned_revision(policy.revision_env)
    return os.environ.get(policy.remote_code_ack_env, "") == REMOTE_CODE_ACK


def verify_bearer_token(
    authorization: str | None,
    *,
    token_env: str,
    allow_legacy_shared_token: bool = False,
) -> None:
    # Imported lazily so the model-loading path can import the other guards
    # without requiring fastapi to be present in that image.
    from fastapi import HTTPException

    expected = os.environ.get(token_env, "")
    if not expected and allow_legacy_shared_token:
        if os.environ.get("ALLOW_LEGACY_SHARED_AGENT_TOKEN", "") == "true":
            expected = os.environ.get("AGENT_API_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail=f"{token_env.lower()}_missing")
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid_token")


def require_qdrant_auth() -> None:
    """
    Qdrant must be authenticated by default.

    Allowing unauthenticated internal Qdrant is permitted only through an
    explicit break-glass flag, useful for isolated local/private lab networks.
    """
    if os.environ.get("QDRANT_API_KEY", "").strip():
        return
    if os.environ.get("ALLOW_UNAUTHENTICATED_QDRANT", "") == "true":
        return
    raise RuntimeError("qdrant_api_key_missing")
