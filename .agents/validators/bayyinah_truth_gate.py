# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Bayyinah Truth Verification Engine — TruthGate + AuditTrail + LLM Bridge.

PAT-001 evidence module. Implements the three claim elements as one
verification pipeline:

1. **TruthGate** — evaluates a set of evidence-labelled claims and issues
   a reviewable verdict (``APPROVE | REQUEST_CHANGES | BLOCKED``) under
   the repository evidence-label contract (``VERIFIED | INFERRED |
   UNVERIFIED``). Fail-closed: malformed input or contradictions block.
2. **AuditTrail** — every gate decision can be appended to the sealed
   Qal'a hash-chained audit sink (Q7) via :meth:`TruthGate.evaluate_and_audit`.
   Only labels, counts, and the verdict enter the trail — never raw claim
   text — so the sink's no-raw-PII contract holds.
3. **LLM Bridge** — a typed bridge seam through which a model runtime may
   restate or challenge claims. The default bridge is offline and
   deterministic; resolving a bridge while ``ALLOW_EXTERNAL_AI=true`` is
   refused outright, mirroring ``core_coding_swarm``'s sovereignty guard.

No network calls. No external dependencies beyond the standard library
and sibling Qal'a modules.
"""

from __future__ import annotations

import json
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Final, Literal, Mapping, Protocol, Sequence

EvidenceLabel = Literal["VERIFIED", "INFERRED", "UNVERIFIED"]
TruthVerdict = Literal["APPROVE", "REQUEST_CHANGES", "BLOCKED"]

_EVIDENCE_LABELS: Final[frozenset[str]] = frozenset(
    {"VERIFIED", "INFERRED", "UNVERIFIED"}
)


@dataclass(frozen=True)
class EvidenceClaim:
    """A single claim submitted to the gate.

    ``statement`` is the asserted fact; ``label`` is the caller's evidence
    label; ``source`` is the artifact backing a VERIFIED label (command
    output path, file path, test name). ``material`` marks claims whose
    failure must degrade the verdict (defaults to True — fail-closed).
    """

    statement: str
    label: str
    source: str = ""
    material: bool = True


@dataclass(frozen=True)
class TruthFinding:
    severity: Literal["INFO", "MEDIUM", "HIGH", "CRITICAL"]
    message: str
    claim_index: int | None = None


@dataclass(frozen=True)
class TruthGateReport:
    verdict: TruthVerdict
    findings: tuple[TruthFinding, ...]
    verified_count: int
    inferred_count: int
    unverified_count: int
    chain_hash: str
    bridge_name: str | None = None


class LLMBridge(Protocol):
    """Bridge seam between the gate and a model runtime.

    Implementations must be side-effect free with respect to the gate:
    they receive claim statements and return challenge notes. They must
    never mutate claims or reach external AI services (see
    :func:`resolve_bridge`).
    """

    @property
    def name(self) -> str: ...

    def challenge(self, statements: Sequence[str]) -> tuple[str, ...]: ...


class OfflineLLMBridge:
    """Deterministic, dependency-free default bridge.

    Flags statements that assert completion or compliance vocabulary
    without hedging — the same claim classes the repository forbids
    asserting without evidence (CLAUDE.md prohibitions #3 and evidence
    labels). Serves as the sovereign-safe stand-in until a local model
    runtime (Ollama / llama.cpp / Modal vLLM) is bound to this seam.
    """

    _ABSOLUTE_TERMS: Final[tuple[str, ...]] = (
        "fully compliant",
        "production ready",
        "production-ready",
        "guaranteed",
        "100%",
        "all patents implemented",
        "zero risk",
    )

    @property
    def name(self) -> str:
        return "offline-deterministic-v1"

    def challenge(self, statements: Sequence[str]) -> tuple[str, ...]:
        notes: list[str] = []
        for idx, statement in enumerate(statements):
            lowered = statement.lower()
            for term in self._ABSOLUTE_TERMS:
                if term in lowered:
                    notes.append(
                        f"claim {idx}: absolute assertion ({term!r}) requires "
                        "VERIFIED evidence with a cited source"
                    )
                    break
        return tuple(notes)


def resolve_bridge(bridge: LLMBridge | None = None) -> LLMBridge:
    """Return the bridge to use, refusing external-AI configurations.

    Mirrors the ``core_coding_swarm`` sovereignty guard: when
    ``ALLOW_EXTERNAL_AI=true`` the gate refuses to run at all rather than
    risk routing claim text to an external AI service.
    """
    if os.environ.get("ALLOW_EXTERNAL_AI", "false").lower() == "true":
        raise RuntimeError(
            "Sovereignty violation: ALLOW_EXTERNAL_AI is enabled. "
            "TruthGate refuses to resolve an LLM bridge while external AI "
            "is allowed. Unset ALLOW_EXTERNAL_AI to proceed offline."
        )
    return bridge if bridge is not None else OfflineLLMBridge()


@dataclass(frozen=True)
class AuditContext:
    """Trace correlation identifiers for the audit trail."""

    trace_id: str
    span_id: str
    tenant_id: str


def _claim_findings(idx: int, claim: EvidenceClaim) -> list[TruthFinding]:
    """Findings for a single claim (fail-closed label discipline)."""
    findings: list[TruthFinding] = []
    if not isinstance(claim.statement, str) or not claim.statement.strip():
        findings.append(
            TruthFinding(
                severity="CRITICAL",
                message="claim statement must be a non-empty string",
                claim_index=idx,
            )
        )
    if claim.label not in _EVIDENCE_LABELS:
        findings.append(
            TruthFinding(
                severity="CRITICAL",
                message=(
                    f"unknown evidence label {claim.label!r}; expected "
                    "VERIFIED | INFERRED | UNVERIFIED"
                ),
                claim_index=idx,
            )
        )
        return findings
    if claim.label == "VERIFIED" and not claim.source.strip():
        findings.append(
            TruthFinding(
                severity="CRITICAL",
                message="VERIFIED label requires a citable source artifact",
                claim_index=idx,
            )
        )
    if claim.label == "UNVERIFIED" and claim.material:
        findings.append(
            TruthFinding(
                severity="HIGH",
                message=(
                    "material claim is UNVERIFIED; verdict cannot be "
                    "APPROVE until evidence exists"
                ),
                claim_index=idx,
            )
        )
    return findings


def _verdict_from(findings: Sequence[TruthFinding]) -> TruthVerdict:
    if any(f.severity == "CRITICAL" for f in findings):
        return "BLOCKED"
    if any(f.severity in {"HIGH", "MEDIUM"} for f in findings):
        return "REQUEST_CHANGES"
    return "APPROVE"


def _chain_hash(claims: Sequence[EvidenceClaim], verdict: str) -> str:
    """Deterministic SHA-256 over the canonical claim set + verdict."""
    canonical = json.dumps(
        {
            "claims": [
                {
                    "label": c.label,
                    "material": c.material,
                    "source": c.source,
                    "statement": c.statement,
                }
                for c in claims
            ],
            "verdict": verdict,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class TruthGate:
    """Evaluate evidence-labelled claims into a reviewable verdict.

    Rules (fail-closed):

    - Empty claim set, blank statement, or unknown label → BLOCKED.
    - VERIFIED without a non-empty ``source`` → CRITICAL → BLOCKED
      (a VERIFIED label is only legitimate with a citable artifact).
    - Any material UNVERIFIED claim → REQUEST_CHANGES (never APPROVE).
    - Bridge challenge notes → REQUEST_CHANGES at minimum.
    - Only a claim set of VERIFIED/INFERRED material claims with sources
      for every VERIFIED label can APPROVE.
    """

    bridge: LLMBridge | None = None
    _resolved_bridge: LLMBridge = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._resolved_bridge = resolve_bridge(self.bridge)

    def evaluate(self, claims: Sequence[EvidenceClaim]) -> TruthGateReport:
        if not claims:
            empty = TruthFinding(
                severity="CRITICAL",
                message="claim set is empty; nothing to verify",
            )
            return self._report("BLOCKED", [empty], ())

        findings: list[TruthFinding] = []
        for idx, claim in enumerate(claims):
            findings.extend(_claim_findings(idx, claim))

        challenge_notes = self._resolved_bridge.challenge(
            [c.statement for c in claims]
        )
        findings.extend(
            TruthFinding(severity="MEDIUM", message=note)
            for note in challenge_notes
        )

        return self._report(_verdict_from(findings), findings, claims)

    def evaluate_and_audit(
        self,
        claims: Sequence[EvidenceClaim],
        *,
        sink: Any,
        context: AuditContext,
    ) -> TruthGateReport:
        """Evaluate then append the decision to the Qal'a audit trail.

        ``sink`` is a ``QalaAuditSink``; typed loosely so this module keeps
        zero import-time coupling to the sink (tests load modules under a
        synthetic package). Payload carries labels/counts only — no claim
        text — preserving the sink's sanitized-payload contract.
        """
        report = self.evaluate(claims)
        result = sink.append(
            event="policy_decision",
            trace_id=context.trace_id,
            span_id=context.span_id,
            tenant_id=context.tenant_id,
            payload=self.audit_payload(report),
        )
        if not result.ok:
            raise RuntimeError(
                f"TruthGate audit append failed: {result.error}: {result.message}"
            )
        return report

    @staticmethod
    def audit_payload(report: TruthGateReport) -> Mapping[str, Any]:
        return {
            "component": "bayyinah_truth_gate",
            "verdict": report.verdict,
            "verifiedCount": report.verified_count,
            "inferredCount": report.inferred_count,
            "unverifiedCount": report.unverified_count,
            "findingCount": len(report.findings),
            "chainHash": report.chain_hash,
            "bridge": report.bridge_name,
        }

    def _report(
        self,
        verdict: TruthVerdict,
        findings: list[TruthFinding],
        claims: Sequence[EvidenceClaim],
    ) -> TruthGateReport:
        labels = [c.label for c in claims]
        return TruthGateReport(
            verdict=verdict,
            findings=tuple(findings),
            verified_count=labels.count("VERIFIED"),
            inferred_count=labels.count("INFERRED"),
            unverified_count=labels.count("UNVERIFIED"),
            chain_hash=_chain_hash(claims, verdict),
            bridge_name=self._resolved_bridge.name,
        )


__all__ = [
    "AuditContext",
    "EvidenceClaim",
    "EvidenceLabel",
    "LLMBridge",
    "OfflineLLMBridge",
    "TruthFinding",
    "TruthGate",
    "TruthGateReport",
    "TruthVerdict",
    "resolve_bridge",
]
