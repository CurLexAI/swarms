# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Auditable Reasoning Chain — ReasoningChainBuilder + DecisionCertificate.

PAT-014 evidence module. A decision pipeline records every reasoning
step through :class:`ReasoningChainBuilder` (usable directly or as a
callable-wrapping middleware); finalizing produces a
:class:`DecisionCertificate` whose ``chain_hash`` is the SHA-256 of the
canonical serialization of the *entire* step chain plus the decision.
Any later mutation of any step invalidates the certificate, which
:func:`verify_certificate` detects.

Complements the Qal'a Q7 sealed audit sink: the sink chains *records
across time*; this module hashes *one decision's internal reasoning* so
the certificate can be stored (e.g. as a ``policy_decision`` payload)
and re-verified independently. Stdlib only; no network calls.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

CHAIN_ALGORITHM = "sha256-canonical-json-v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ReasoningStep:
    index: int
    actor: str
    action: str
    rationale: str
    occurred_at: str


@dataclass(frozen=True)
class DecisionCertificate:
    certificate_version: int
    algorithm: str
    decision: str
    step_count: int
    chain_hash: str
    issued_at: str
    tenant_id: str
    trace_id: str


def _canonical_chain(steps: Sequence[ReasoningStep], decision: str) -> str:
    # Key-sorted, separator-stable JSON so the hash is reproducible across
    # runs and languages (same convention as qala_audit_sink).
    return json.dumps(
        {
            "decision": decision,
            "steps": [
                {
                    "action": s.action,
                    "actor": s.actor,
                    "index": s.index,
                    "occurredAt": s.occurred_at,
                    "rationale": s.rationale,
                }
                for s in steps
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class ReasoningChainBuilder:
    """Accumulates reasoning steps and mints a decision certificate."""

    def __init__(self, *, tenant_id: str, trace_id: str) -> None:
        if not tenant_id or not trace_id:
            raise ValueError("tenant_id and trace_id are required")
        self._tenant_id = tenant_id
        self._trace_id = trace_id
        self._steps: list[ReasoningStep] = []
        self._sealed = False

    @property
    def steps(self) -> tuple[ReasoningStep, ...]:
        return tuple(self._steps)

    def add_step(
        self,
        *,
        actor: str,
        action: str,
        rationale: str,
        occurred_at: str | None = None,
    ) -> ReasoningStep:
        if self._sealed:
            raise RuntimeError("chain is sealed; no further steps may be added")
        if not actor.strip() or not action.strip():
            raise ValueError("actor and action must be non-empty")
        step = ReasoningStep(
            index=len(self._steps),
            actor=actor,
            action=action,
            rationale=rationale,
            occurred_at=occurred_at if occurred_at is not None else _now_iso(),
        )
        self._steps.append(step)
        return step

    def record(
        self,
        fn: Callable[[], Any],
        *,
        actor: str,
        action: str,
    ) -> Any:
        """Middleware form: run ``fn`` and record it as one step.

        ``fn`` takes no arguments — bind any with ``functools.partial``
        or a lambda. The step's rationale carries the outcome class only
        (``ok`` or the exception type) — never raw return values, so
        sensitive material cannot leak into certificates by default.
        """
        try:
            result = fn()
        except Exception as exc:
            self.add_step(
                actor=actor,
                action=action,
                rationale=f"raised {type(exc).__name__}",
            )
            raise
        self.add_step(actor=actor, action=action, rationale="ok")
        return result

    def build_certificate(self, *, decision: str) -> DecisionCertificate:
        """Seal the chain and mint the certificate.

        Fail-closed: an empty chain cannot certify a decision. Sealing is
        one-way — the builder refuses further steps afterwards, so a
        certificate always covers the full and final chain.
        """
        if not decision.strip():
            raise ValueError("decision must be non-empty")
        if not self._steps:
            raise ValueError("cannot certify a decision with no reasoning steps")
        self._sealed = True
        return DecisionCertificate(
            certificate_version=1,
            algorithm=CHAIN_ALGORITHM,
            decision=decision,
            step_count=len(self._steps),
            chain_hash=_sha256(_canonical_chain(self._steps, decision)),
            issued_at=_now_iso(),
            tenant_id=self._tenant_id,
            trace_id=self._trace_id,
        )


def verify_certificate(
    certificate: DecisionCertificate, steps: Sequence[ReasoningStep]
) -> bool:
    """Recompute the chain hash from ``steps`` and compare.

    Returns False on any mismatch — step count, algorithm, or hash —
    rather than raising, so callers can branch fail-closed.
    """
    if certificate.algorithm != CHAIN_ALGORITHM:
        return False
    if certificate.step_count != len(steps):
        return False
    recomputed = _sha256(_canonical_chain(steps, certificate.decision))
    return recomputed == certificate.chain_hash


def certificate_audit_payload(
    certificate: DecisionCertificate,
) -> Mapping[str, Any]:
    """Sanitized payload for the Qal'a audit sink (labels/hashes only)."""
    return {
        "component": "reasoning_chain",
        "algorithm": certificate.algorithm,
        "decision": certificate.decision,
        "stepCount": certificate.step_count,
        "chainHash": certificate.chain_hash,
        "issuedAt": certificate.issued_at,
    }


__all__ = [
    "CHAIN_ALGORITHM",
    "DecisionCertificate",
    "ReasoningChainBuilder",
    "ReasoningStep",
    "certificate_audit_payload",
    "verify_certificate",
]
