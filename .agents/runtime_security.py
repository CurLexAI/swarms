# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
Runtime security primitives for the Modal agent runtime.
=========================================================
Fail-closed helpers shared by `.agents/modal_app.py` and `.agents/ingest_test.py`:

* `require_pinned_revision` / `trust_remote_code_for` — supply-chain guard that
  refuses to load a model from a mutable ref or to execute remote model code
  unless a pinned commit SHA AND a deliberate acknowledgement are both present.
* `verify_bearer_token` — endpoint-specific Bearer auth with no shared-token
  fallback path.
* `require_qdrant_auth` — Qdrant must be authenticated unless an explicit
  break-glass flag is set for an isolated, network-protected lab instance.

These helpers are intentionally dependency-light: `fastapi` is imported lazily
inside `verify_bearer_token` so the model-loading path (which runs inside the
GPU container) can import the revision/Qdrant guards without pulling in fastapi.
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import re
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

FULL_COMMIT_SHA: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
REMOTE_CODE_ACK: Final[str] = "ALLOW_PINNED_REVIEWED_REMOTE_CODE"
LOCAL_ENVIRONMENT_NAMES: Final[frozenset[str]] = frozenset({"dev", "development", "local", "test"})
PRODUCTION_ENVIRONMENT_NAMES: Final[frozenset[str]] = frozenset({"prod", "production"})


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
) -> None:
    # Imported lazily so the model-loading path can import the other guards
    # without requiring fastapi to be present in that image.
    from fastapi import HTTPException

    expected = os.environ.get(token_env, "")
    if not expected:
        raise HTTPException(status_code=503, detail=f"{token_env.lower()}_missing")
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")
    if not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid_token")


def _current_environment_names() -> set[str]:
    """Return normalized runtime environment labels from common env vars.

    Returns:
        Lower-case environment labels from ``ENVIRONMENT``, ``APP_ENV``,
        ``MODAL_ENVIRONMENT``, and ``NODE_ENV`` after empty values are removed.
    """

    return {
        value.strip().lower()
        for name in ("ENVIRONMENT", "APP_ENV", "MODAL_ENVIRONMENT", "NODE_ENV")
        if (value := os.environ.get(name, "")).strip()
    }


def _host_is_private_or_local(url: str) -> bool:
    """Return whether a URL host is constrained to local/private networking.

    Args:
        url: Qdrant URL from ``QDRANT_INTERNAL_URL``.

    Returns:
        ``True`` for localhost names, private/link-local/loopback IPs, and
        single-label service names used by local compose networks.
    """

    host = (urlparse(url).hostname or "").strip().lower()
    if not host:
        return False
    if host in {"localhost"} or host.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "." not in host
    return address.is_private or address.is_loopback or address.is_link_local


def require_qdrant_auth() -> None:
    """Require Qdrant API-key authentication outside isolated local/dev labs.

    Production or externally reachable runtimes must provide ``QDRANT_API_KEY``.
    The unauthenticated break-glass path is accepted only when all of these are
    true: the explicit flag is set, the runtime environment is local/dev/test,
    and ``QDRANT_INTERNAL_URL`` resolves to a local/private-network host.

    Raises:
        RuntimeError: If Qdrant auth is missing for production/reachable runtime
            or if break-glass was requested outside the allowed local boundary.
    """

    if os.environ.get("QDRANT_API_KEY", "").strip():
        return

    environments = _current_environment_names()
    if environments & PRODUCTION_ENVIRONMENT_NAMES:
        raise RuntimeError("qdrant_api_key_required_in_production")

    break_glass = os.environ.get("ALLOW_UNAUTHENTICATED_QDRANT", "") == "true"
    if not break_glass:
        raise RuntimeError("qdrant_api_key_missing")

    if not environments or not environments <= LOCAL_ENVIRONMENT_NAMES:
        raise RuntimeError("qdrant_unauthenticated_requires_local_dev_environment")

    if not _host_is_private_or_local(os.environ.get("QDRANT_INTERNAL_URL", "")):
        raise RuntimeError("qdrant_unauthenticated_requires_private_network")
