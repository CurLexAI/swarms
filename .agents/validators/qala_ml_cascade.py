# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Cascaded ML Security Gate — staged classifiers, SAFE/WARNING/BLOCKED.

PAT-004 evidence module. Implements the cascade *architecture* of the
claim: three ordered classifier stages (code-threat, prompt-injection,
PII) evaluated under a CPU latency budget of 200ms, emitting a single
``SAFE | WARNING | BLOCKED`` verdict with per-stage results.

Model stages are pluggable through :class:`CascadeStage`. The defaults
shipped here are deterministic, dependency-free classifiers so the gate
is executable and testable inside the repository's no-model-download
policy (``.agents/policies/dependency-build-safety.md``). The slot names
(``codebert-code-threat``, ``modernbert-prompt-injection``,
``bert-small-ksa-pii``) mark where the corresponding transformer models
bind when a sovereign model runtime is provisioned; binding them is a
deployment step, not a code change.

Cascade semantics: stages run in declared order; the first BLOCK
short-circuits the cascade (cheapest-stage-first cost model); WARN
results accumulate. Fail-closed: a stage raising is treated as BLOCK.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Final, Literal, Protocol, Sequence

from . import qala_ksa_pii

CascadeVerdict = Literal["SAFE", "WARNING", "BLOCKED"]
StageLabel = Literal["PASS", "WARN", "BLOCK"]

LATENCY_BUDGET_MS: Final[float] = 200.0


@dataclass(frozen=True)
class StageResult:
    stage: str
    label: StageLabel
    detail: str
    elapsed_ms: float


@dataclass(frozen=True)
class CascadeReport:
    verdict: CascadeVerdict
    stages: tuple[StageResult, ...]
    elapsed_ms: float
    within_budget: bool
    budget_ms: float


class CascadeStage(Protocol):
    """A single classifier slot in the cascade."""

    @property
    def name(self) -> str: ...

    def classify(self, text: str) -> tuple[StageLabel, str]: ...


_CODE_THREAT_TERMS: Final[tuple[str, ...]] = (
    "rm -rf",
    "curl ",
    "wget ",
    "subprocess.popen",
    "os.system",
    "eval(",
    "exec(",
    "requests.post",
    "requests.get",
    "urllib.request",
    "fetch(",
    "xmlhttprequest",
)

_CODE_WARN_TERMS: Final[tuple[str, ...]] = (
    "chmod ",
    "base64 -d",
    "pickle.loads",
)


class CodeThreatStage:
    """Deterministic default for the ``codebert-code-threat`` slot."""

    @property
    def name(self) -> str:
        return "codebert-code-threat"

    def classify(self, text: str) -> tuple[StageLabel, str]:
        lowered = text.lower()
        for term in _CODE_THREAT_TERMS:
            if term in lowered:
                return ("BLOCK", f"dangerous execution pattern: {term!r}")
        for term in _CODE_WARN_TERMS:
            if term in lowered:
                return ("WARN", f"suspicious execution pattern: {term!r}")
        return ("PASS", "no code-threat pattern")


_INJECTION_BLOCK_TERMS: Final[tuple[str, ...]] = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "reveal the system prompt",
    "leak token",
    "bypass policy",
    "تجاهل التعليمات",
)

_INJECTION_WARN_TERMS: Final[tuple[str, ...]] = (
    "system prompt",
    "developer message",
)


class PromptInjectionStage:
    """Deterministic default for the ``modernbert-prompt-injection`` slot."""

    @property
    def name(self) -> str:
        return "modernbert-prompt-injection"

    def classify(self, text: str) -> tuple[StageLabel, str]:
        lowered = text.lower()
        for term in _INJECTION_BLOCK_TERMS:
            if term.lower() in lowered:
                return ("BLOCK", f"prompt-injection phrase: {term!r}")
        for term in _INJECTION_WARN_TERMS:
            if term in lowered:
                return ("WARN", f"instruction-surface reference: {term!r}")
        return ("PASS", "no injection phrase")


class KsaPiiStage:
    """Deterministic default for the ``bert-small-ksa-pii`` slot.

    Delegates to the Q5 KSA-PII detector; any sovereign identifier is a
    hard BLOCK (consistent with qala_input_gate's CRITICAL handling).
    """

    @property
    def name(self) -> str:
        return "bert-small-ksa-pii"

    def classify(self, text: str) -> tuple[StageLabel, str]:
        hits = qala_ksa_pii.detect_ksa_pii(text)
        if hits:
            categories = ",".join(sorted({h.category for h in hits}))
            return ("BLOCK", f"KSA PII detected: {categories}")
        return ("PASS", "no KSA PII")


def default_stages() -> tuple[CascadeStage, ...]:
    return (CodeThreatStage(), PromptInjectionStage(), KsaPiiStage())


class CascadedSecurityGate:
    """Run the stage cascade over an input under a latency budget."""

    def __init__(
        self,
        stages: Sequence[CascadeStage] | None = None,
        *,
        budget_ms: float = LATENCY_BUDGET_MS,
    ) -> None:
        if budget_ms <= 0:
            raise ValueError("budget_ms must be positive")
        self._stages: tuple[CascadeStage, ...] = (
            tuple(stages) if stages is not None else default_stages()
        )
        if not self._stages:
            raise ValueError("cascade requires at least one stage")
        self._budget_ms = budget_ms

    def scan(self, text: str) -> CascadeReport:
        if not isinstance(text, str) or not text.strip():
            # Fail-closed on unusable input.
            return CascadeReport(
                verdict="BLOCKED",
                stages=(
                    StageResult(
                        stage="input-shape",
                        label="BLOCK",
                        detail="input must be a non-empty string",
                        elapsed_ms=0.0,
                    ),
                ),
                elapsed_ms=0.0,
                within_budget=True,
                budget_ms=self._budget_ms,
            )

        started = time.perf_counter()
        results: list[StageResult] = []
        verdict: CascadeVerdict = "SAFE"

        for stage in self._stages:
            stage_started = time.perf_counter()
            try:
                label, detail = stage.classify(text)
            except Exception as exc:  # fail-closed: a broken stage blocks
                label, detail = ("BLOCK", f"stage error: {exc}")
            stage_elapsed = (time.perf_counter() - stage_started) * 1000.0
            results.append(
                StageResult(
                    stage=stage.name,
                    label=label,
                    detail=detail,
                    elapsed_ms=stage_elapsed,
                )
            )
            if label == "BLOCK":
                verdict = "BLOCKED"
                break  # short-circuit: later (costlier) stages are skipped
            if label == "WARN" and verdict == "SAFE":
                verdict = "WARNING"

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return CascadeReport(
            verdict=verdict,
            stages=tuple(results),
            elapsed_ms=elapsed_ms,
            within_budget=elapsed_ms <= self._budget_ms,
            budget_ms=self._budget_ms,
        )


__all__ = [
    "CascadeReport",
    "CascadeStage",
    "CascadeVerdict",
    "CascadedSecurityGate",
    "CodeThreatStage",
    "KsaPiiStage",
    "LATENCY_BUDGET_MS",
    "PromptInjectionStage",
    "StageLabel",
    "StageResult",
    "default_stages",
]
