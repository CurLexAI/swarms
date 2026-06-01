#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
LexPrim ↔ swarms Bridge (ADR-0001 Compliant)
============================================
Unidirectional adapter: LexPrim → swarms only.

Translates requests from LexPrim agents (CAO-Claude, CGSA-Gemini, VPE-FORGE)
to swarms agents (Mihwar, Bayyinah) without adding new services or autoStart flags.

Audit log: Local append-only JSONL file (bridge_audit.jsonl).
Invocation: CLI (local) → GitHub Actions (automated).

Rules enforced:
- No REST endpoints (violates ADR-0001).
- No bidirectional calls (prevents circular dependencies).
- No persistent services.
- All requests logged locally for SAMA CSF / PDPL compliance.
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

# ── Enums ──────────────────────────────────────────────────────────────

class SourceAgent(str, Enum):
    """LexPrim agents that can request translations."""
    CAO_CLAUDE = "cao-claude"        # Chief Architect Officer (Claude)
    CGSA_GEMINI = "cgsa-gemini"      # Chief Governance & Security (Gemini)
    VPE_FORGE = "vpe-forge"          # Vice President Engineering (FORGE)
    RAPTOR = "raptor"                # Supreme Commander


class TargetAgent(str, Enum):
    """swarms agents that can fulfill requests."""
    MIHWAR = "mihwar"                # Architect & Code Generator
    BAYYINAH = "bayyinah"            # Auditor & Code Reviewer


class RequestStatus(str, Enum):
    """Status of a bridge request."""
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


# ── Data Models ────────────────────────────────────────────────────────

@dataclass
class BridgeRequest:
    """Incoming request from LexPrim."""
    source: SourceAgent
    task: str
    target: Optional[TargetAgent] = None
    context: Optional[str] = None
    priority: str = "NORMAL"  # NORMAL / HIGH / CRITICAL
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class BridgeResponse:
    """Outgoing response to LexPrim."""
    request_id: str
    source: SourceAgent
    target: TargetAgent
    result: str
    status: RequestStatus
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Serialize for audit log."""
        data = asdict(self)
        data["status"] = self.status.value
        data["source"] = self.source.value
        data["target"] = self.target.value
        return data


# ── Configuration ──────────────────────────────────────────────────────

BRIDGE_AUDIT_LOG = Path(__file__).parent.parent / "audit" / "bridge_audit.jsonl"
BRIDGE_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

# Mapping: LexPrim source → swarms target
SOURCE_TO_TARGET = {
    SourceAgent.CAO_CLAUDE: TargetAgent.MIHWAR,      # Architecture → Code Generation
    SourceAgent.CGSA_GEMINI: TargetAgent.BAYYINAH,   # Security Audit → Code Review
    SourceAgent.VPE_FORGE: TargetAgent.MIHWAR,       # Execution → Code Generation
    SourceAgent.RAPTOR: TargetAgent.MIHWAR,          # Supreme Command → Architecture
}


# ── Audit Logging ──────────────────────────────────────────────────────

def _log_audit(response: BridgeResponse) -> None:
    """
    Write response to append-only audit log (JSONL format).
    Compliant with SAMA CSF and PDPL auditability requirements.
    """
    try:
        with open(BRIDGE_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(response.to_dict(), ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[⚠️] Failed to write audit log: {e}", file=sys.stderr)


# ── Main Bridge ────────────────────────────────────────────────────────

class LexPrimBridge:
    """
    Unidirectional bridge from LexPrim to swarms.

    Responsibilities:
    1. Accept requests from LexPrim agents (CAO-Claude, CGSA-Gemini, VPE-FORGE).
    2. Infer or map to swarms targets (Mihwar, Bayyinah).
    3. Invoke swarms agents via invoke.py (CLI mode).
    4. Log all transactions for audit (SAMA CSF, PDPL).
    5. Return response to LexPrim.

    Constraints (ADR-0001):
    - No new REST endpoints.
    - No bidirectional calls (LexPrim → swarms only).
    - No autoStart or persistent services.
    - Local audit log only (no Qdrant ingestion).
    """

    def __init__(self, invoke_module_path: Optional[str] = None):
        """
        Initialize the bridge.

        Args:
            invoke_module_path: Path to .agents/invoke.py (for testing).
        """
        self.invoke_path = invoke_module_path or (
            Path(__file__).parent.parent / "invoke.py"
        )

    async def process(self, request: BridgeRequest) -> BridgeResponse:
        """
        Process a single translation request.

        Steps:
        1. Validate source agent.
        2. Infer or validate target agent.
        3. Call swarms agent (Mihwar or Bayyinah).
        4. Log the transaction.
        5. Return response.
        """
        start_time = datetime.now(timezone.utc)

        # Infer target if not specified
        target = request.target or self._infer_target(request.source)

        print(
            f"[🌉 Bridge] → {request.source.value} requests {target.value} "
            f"(ID: {request.request_id})"
        )

        try:
            if target == TargetAgent.MIHWAR:
                result = await self._invoke_mihwar(request.task, request.context)
            elif target == TargetAgent.BAYYINAH:
                result = await self._invoke_bayyinah(request.task)
            else:
                raise ValueError(f"Unknown target: {target}")

            status = RequestStatus.SUCCESS
            error = None

        except Exception as e:
            result = ""
            status = RequestStatus.FAILED
            error = str(e)
            print(f"[❌ Bridge] Error: {error}", file=sys.stderr)

        # Calculate duration
        duration_ms = (
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        # Build response
        response = BridgeResponse(
            request_id=request.request_id,
            source=request.source,
            target=target,
            result=result,
            status=status,
            error=error,
            duration_ms=duration_ms,
        )

        # Audit log
        _log_audit(response)

        print(
            f"[✅ Bridge] ← {target.value} returns {status.value} "
            f"({duration_ms:.0f}ms)"
        )

        return response

    def _infer_target(self, source: SourceAgent) -> TargetAgent:
        """
        Infer the swarms target from the LexPrim source.

        Mapping:
        - CAO-Claude (architect) → Mihwar (code generator)
        - CGSA-Gemini (security) → Bayyinah (code reviewer)
        - VPE-FORGE (executor) → Mihwar (code generator)
        - RAPTOR (commander) → Mihwar (architect)
        """
        return SOURCE_TO_TARGET.get(source, TargetAgent.MIHWAR)

    async def _invoke_mihwar(self, task: str, context: Optional[str] = None) -> str:
        """
        Invoke Mihwar via invoke.py (CLI mode).

        This calls the swarms Mihwar agent to generate code or architecture.
        """
        import subprocess

        cmd = [
            str(sys.executable),
            str(self.invoke_path),
            "mihwar",
            task,
        ]

        if context:
            cmd += ["--context", context]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Mihwar failed: {result.stderr}")

        return result.stdout.strip()

    async def _invoke_bayyinah(self, code_or_task: str) -> str:
        """
        Invoke Bayyinah via invoke.py (CLI mode).

        This calls the swarms Bayyinah agent to review code.
        """
        import subprocess

        cmd = [
            str(sys.executable),
            str(self.invoke_path),
            "bayyinah",
            "--code",
            code_or_task,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Bayyinah failed: {result.stderr}")

        return result.stdout.strip()


# ── CLI Interface ──────────────────────────────────────────────────────

async def main_cli() -> int:
    """
    CLI entry point for local testing.

    Usage:
        python .agents/adapters/lexprim_bridge.py cao-claude "Design auth system"
        python .agents/adapters/lexprim_bridge.py cgsa-gemini "Review security"
    """
    if len(sys.argv) < 3:
        print(
            "Usage: lexprim_bridge.py <source> <task>\n"
            "  source: cao-claude | cgsa-gemini | vpe-forge | raptor\n"
            "  task: description of work"
        )
        return 1

    source_str = sys.argv[1].lower()
    task = " ".join(sys.argv[2:])

    # Parse source
    try:
        source = SourceAgent(source_str)
    except ValueError:
        print(f"Invalid source: {source_str}", file=sys.stderr)
        return 1

    # Create request
    request = BridgeRequest(source=source, task=task)

    # Process
    bridge = LexPrimBridge()
    response = await bridge.process(request)

    # Print result
    if response.status == RequestStatus.SUCCESS:
        print(f"\n{response.result}")
        return 0
    else:
        print(f"Error: {response.error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main_cli())
    sys.exit(exit_code)
