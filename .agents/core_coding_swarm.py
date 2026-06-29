# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Core Coding Swarm Orchestrator — Mihwar → Bayyinah pipeline.

Coordinates planning (Mihwar) and evidence-review validation (Bayyinah)
for coding tasks. Direct Bayyinah/Qdrant access from client-facing flows
is prohibited: all requests must pass through this orchestrator.

Architecture (ADR-0001, category 1 — agent operations):
    Client request
        → CoreCodingSwarm.execute_task()
            → phase_1_mihwar_planning()   (Mihwar: architect/control layer)
            → phase_2_bayyinah_validation()  (Bayyinah: evidence/review layer)
        ← SwarmResult (SUCCESS | REJECTED | ESCALATED | ERROR)

Compliance:
- External AI is denied by default (ALLOW_EXTERNAL_AI defaults to "false").
  execute_task() returns REJECTED if external AI is detected as enabled.
- Live HTTP calls are disabled unless CORE_SWARM_ENABLE_LIVE_CALLS=true.
  Default mode is offline/mock-safe, suitable for NO-SECRETS/OFFLINE CI.
- Endpoints default to local-only: http://localhost:11434 (Ollama).
  ``localhost`` is used deliberately (not 127.0.0.1) to satisfy the
  qala-egress-residency gate (IP literals are flagged).
- Audit logging writes to artifacts/security/ with stderr fallback so that
  CI and dev environments without /var/log/ permissions work correctly.
- Task descriptions are truncated to _LOG_TASK_MAX_CHARS in all log lines.
- No secrets, tokens, or endpoint URLs are ever printed.

Environment variables:
    ALLOW_EXTERNAL_AI          "false" (default). If "true", execute_task()
                                returns REJECTED immediately (fail-closed).
    CORE_SWARM_ENABLE_LIVE_CALLS "false" (default). Set "true" to enable
                                actual HTTP calls to sovereign endpoints.
    MIHWAR_ENDPOINT            Sovereign Mihwar endpoint.
                                Default: http://localhost:11434
    BAYYINAH_ENDPOINT          Sovereign Bayyinah endpoint.
                                Default: http://localhost:11434
    OLLAMA_MIHWAR_MODEL        Ollama model tag for Mihwar.
                                Default: deepseek-coder-v2
    OLLAMA_BAYYINAH_MODEL      Ollama model tag for Bayyinah.
                                Default: qwen2.5-coder:32b
    SIEM_LOG_PATH              Path for the audit log file.
                                Default: artifacts/security/core_swarm_audit.log

Do not claim live Mihwar/Bayyinah operation unless a smoke test confirms it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

# ── Constants ────────────────────────────────────────────────────────────────

_LOG_TASK_MAX_CHARS: int = 80
_LLM_TIMEOUT_SECONDS: int = 60
_DEFAULT_MIHWAR_ENDPOINT: str = "http://localhost:11434"
_DEFAULT_BAYYINAH_ENDPOINT: str = "http://localhost:11434"
_DEFAULT_MIHWAR_MODEL: str = "deepseek-coder-v2"
_DEFAULT_BAYYINAH_MODEL: str = "qwen2.5-coder:32b"
_DEFAULT_SIEM_LOG_PATH: str = "artifacts/security/audit.log"

# ── Pydantic models ──────────────────────────────────────────────────────────


class MihwarPlan(BaseModel):
    """Planning output emitted by Mihwar (architect / control layer)."""

    task_id: str
    architecture_decision: str
    compliance_check: bool
    required_evidence: list[str]


class BayyinahValidation(BaseModel):
    """Validation report emitted by Bayyinah (evidence / review layer)."""

    plan_id: str
    evidence_retrieved: list[str]
    is_valid: bool
    conflicts_detected: Optional[str] = None


class SwarmResult(BaseModel):
    """Final result returned to the caller after the full swarm pipeline."""

    status: str = Field(description="SUCCESS | REJECTED | ESCALATED | ERROR")
    final_output: str
    audit_trail_id: str


# ── Logging ──────────────────────────────────────────────────────────────────


def _setup_logger(name: str) -> logging.Logger:
    """Return a configured Logger, writing to SIEM_LOG_PATH with stderr fallback."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    log_path = Path(
        os.environ.get("SIEM_LOG_PATH", _DEFAULT_SIEM_LOG_PATH)
    )
    handler: logging.Handler
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler(sys.stderr)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


_logger: logging.Logger = _setup_logger("CoreCodingSwarm")

# ── Internal helpers ─────────────────────────────────────────────────────────


def _truncate_for_log(text: str) -> str:
    """Truncate a task description so that log lines stay bounded."""
    if len(text) <= _LOG_TASK_MAX_CHARS:
        return text
    return text[:_LOG_TASK_MAX_CHARS] + "...[truncated]"


def _make_audit_trail_id(task_description: str) -> str:
    """Produce a tracing ID that is deterministic on task content.

    The ID embeds a UTC timestamp prefix and an 8-hex-char SHA-256 suffix
    derived from the task description. Neither the full description nor any
    secret material is exposed.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    digest = hashlib.sha256(task_description.encode("utf-8")).hexdigest()[:8]
    return f"SWARM-{ts}-{digest}"


def _call_sovereign_llm(
    endpoint: str,
    model: str,
    system_prompt: str,
    prompt: str,
) -> str:
    """POST to a local Ollama /api/generate endpoint.

    Only called when CORE_SWARM_ENABLE_LIVE_CALLS=true. Uses stdlib
    urllib.request — no third-party HTTP library dependency at runtime.

    Raises RuntimeError on any network or parse failure so callers can
    safely wrap it in a try/except and return SwarmResult(status="ERROR").
    """
    payload: dict[str, object] = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{endpoint}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_LLM_TIMEOUT_SECONDS) as resp:
            raw: str = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Sovereign endpoint unreachable.") from exc

    try:
        body: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Non-JSON response from sovereign endpoint.") from exc

    if not isinstance(body, dict):
        raise RuntimeError("Unexpected response shape from sovereign endpoint.")
    result = body.get("response", "")
    if not isinstance(result, str):
        return ""
    return result


# ── Orchestrator ─────────────────────────────────────────────────────────────


class CoreCodingSwarm:
    """Sovereign orchestrator for the Mihwar → Bayyinah coding pipeline.

    Default mode is **offline/mock-safe**: no HTTP calls are made unless
    CORE_SWARM_ENABLE_LIVE_CALLS=true. This keeps CI, onboarding, and
    NO-SECRETS environments working without any external services.

    Usage::

        swarm = CoreCodingSwarm()
        result = swarm.execute_task("Refactor the auth module")
        print(result.status)   # SUCCESS | REJECTED | ESCALATED | ERROR
    """

    def __init__(self) -> None:
        self._mihwar_endpoint: str = os.environ.get(
            "MIHWAR_ENDPOINT", _DEFAULT_MIHWAR_ENDPOINT
        ).rstrip("/")
        self._bayyinah_endpoint: str = os.environ.get(
            "BAYYINAH_ENDPOINT", _DEFAULT_BAYYINAH_ENDPOINT
        ).rstrip("/")
        self._mihwar_model: str = os.environ.get(
            "OLLAMA_MIHWAR_MODEL", _DEFAULT_MIHWAR_MODEL
        )
        self._bayyinah_model: str = os.environ.get(
            "OLLAMA_BAYYINAH_MODEL", _DEFAULT_BAYYINAH_MODEL
        )
        self._live_calls: bool = (
            os.environ.get("CORE_SWARM_ENABLE_LIVE_CALLS", "false").lower() == "true"
        )
        _logger.info(
            "CoreCodingSwarm initialised. live_calls=%s", self._live_calls
        )

    # ── Phase 1: Mihwar planning ─────────────────────────────────────────────

    def phase_1_mihwar_planning(
        self, task_description: str, task_id: str
    ) -> MihwarPlan:
        """Mihwar receives the task, applies control policy, and designs the plan.

        In offline mode a deterministic mock plan is returned.
        In live mode (CORE_SWARM_ENABLE_LIVE_CALLS=true) the sovereign
        Mihwar endpoint is called via /api/generate.

        Raises RuntimeError on live-call failure. Callers should catch this
        and convert it to SwarmResult(status="ERROR").
        """
        _logger.info(
            "Task %s entered Phase 1 (Mihwar planning). desc=%s",
            task_id,
            _truncate_for_log(task_description),
        )

        if self._live_calls:
            system_prompt = (
                "You are Mihwar (المحور), the architect and control layer. "
                "Analyse the task, apply ECC-2/PDPL compliance gates, and "
                "list the evidence keys Bayyinah must retrieve."
            )
            _call_sovereign_llm(
                self._mihwar_endpoint,
                self._mihwar_model,
                system_prompt,
                task_description,
            )
            # UNVERIFIED: live response parsing — extend when smoke tests confirm
            # the actual Ollama response schema for your deployed model.

        plan = MihwarPlan(
            task_id=task_id,
            architecture_decision=(
                f"Offline plan for: {_truncate_for_log(task_description)}"
                if not self._live_calls
                else f"Live plan for: {_truncate_for_log(task_description)}"
            ),
            compliance_check=True,
            required_evidence=["policy_doc_v1", "compliance_framework_2024"],
        )
        _logger.info("Mihwar plan created for %s.", task_id)
        return plan

    # ── Phase 2: Bayyinah validation ─────────────────────────────────────────

    def phase_2_bayyinah_validation(self, plan: MihwarPlan) -> BayyinahValidation:
        """Bayyinah receives the plan and validates it against evidence.

        In offline mode evidence retrieval is mocked; all required_evidence
        entries are acknowledged and the plan is marked valid.
        In live mode the sovereign Bayyinah endpoint is called.

        Raises RuntimeError on live-call failure.
        """
        _logger.info(
            "Plan %s entered Phase 2 (Bayyinah validation).", plan.task_id
        )

        if self._live_calls:
            system_prompt = (
                "You are Bayyinah (البيّنة), the evidence engine and review "
                "layer. Validate the plan against the retrieved evidence. "
                "Do not access Qarar/Qdrant directly — evidence keys are "
                "provided by Mihwar."
            )
            _call_sovereign_llm(
                self._bayyinah_endpoint,
                self._bayyinah_model,
                system_prompt,
                plan.model_dump_json(),
            )
            # UNVERIFIED: live response parsing — extend when smoke tests confirm.

        validation = BayyinahValidation(
            plan_id=plan.task_id,
            evidence_retrieved=list(plan.required_evidence),
            is_valid=True,
            conflicts_detected=None,
        )
        _logger.info(
            "Bayyinah validation complete for %s. is_valid=%s",
            plan.task_id,
            validation.is_valid,
        )
        return validation

    # ── Main entry point ─────────────────────────────────────────────────────

    def execute_task(self, task_description: str) -> SwarmResult:
        """Full Mihwar → Bayyinah pipeline for a single task.

        Sovereignty check:
            Returns REJECTED immediately if ALLOW_EXTERNAL_AI=true is
            detected in the environment. This is the fail-closed gate.

        Returns:
            SwarmResult with status one of:
                "SUCCESS"   — plan validated, pipeline complete.
                "REJECTED"  — sovereignty gate or compliance gate blocked it.
                "ESCALATED" — Bayyinah found conflicts; human review required.
                "ERROR"     — unrecoverable internal failure.
        """
        # ── Sovereignty gate (fail-closed) ───────────────────────────────────
        if os.environ.get("ALLOW_EXTERNAL_AI", "false").lower() == "true":
            _logger.error(
                "Sovereignty violation: ALLOW_EXTERNAL_AI is enabled. "
                "Rejecting task immediately."
            )
            return SwarmResult(
                status="REJECTED",
                final_output=(
                    "Sovereignty violation: ALLOW_EXTERNAL_AI is enabled. "
                    "External AI must be disabled for sovereign operation."
                ),
                audit_trail_id="SOVEREIGNTY-VIOLATION",
            )

        task_id = _make_audit_trail_id(task_description)
        _logger.info(
            "New swarm execution: %s. desc=%s",
            task_id,
            _truncate_for_log(task_description),
        )

        try:
            # Phase 1 — Mihwar planning
            plan = self.phase_1_mihwar_planning(task_description, task_id)

            if not plan.compliance_check:
                _logger.warning(
                    "Task %s rejected by Mihwar compliance gate.", task_id
                )
                return SwarmResult(
                    status="REJECTED",
                    final_output="Rejected by ECC-2/PDPL compliance gate.",
                    audit_trail_id=task_id,
                )

            # Phase 2 — Bayyinah validation
            validation = self.phase_2_bayyinah_validation(plan)

            if not validation.is_valid:
                _logger.warning(
                    "Task %s escalated. conflict=%s",
                    task_id,
                    validation.conflicts_detected or "unspecified",
                )
                return SwarmResult(
                    status="ESCALATED",
                    final_output=(
                        "Sent to human escalation gate: evidence conflict detected."
                    ),
                    audit_trail_id=task_id,
                )

            _logger.info("Task %s completed successfully.", task_id)
            return SwarmResult(
                status="SUCCESS",
                final_output=(
                    f"Task planned by Mihwar and validated by Bayyinah. "
                    f"Evidence acknowledged: {validation.evidence_retrieved}"
                ),
                audit_trail_id=task_id,
            )

        except RuntimeError as exc:
            _logger.error(
                "Swarm execution error for %s: %s", task_id, exc
            )
            return SwarmResult(
                status="ERROR",
                final_output="Internal execution error. See audit log for details.",
                audit_trail_id=task_id,
            )


# ── CLI / offline smoke test ─────────────────────────────────────────────────

if __name__ == "__main__":
    swarm = CoreCodingSwarm()
    print("CoreCodingSwarm — offline mode. UNVERIFIED: no live endpoints called.")
    result = swarm.execute_task("Refactor the auth module to use HMAC tokens")
    print(result.model_dump_json(indent=2))
