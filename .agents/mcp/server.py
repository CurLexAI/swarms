# SPDX-License-Identifier: MIT
# Licensed under MIT
"""MCP server exposing Mihwar and Bayyinah agents as MCP tools via local Ollama.

This server speaks the Model Context Protocol over stdio and forwards
tool calls to a local Ollama instance. The tools are MCP-exposed
surfaces, consumable by any MCP-compatible client: GitHub Copilot,
Claude Desktop, Cursor, Continue, or a direct stdio peer.

Aegis sits at this MCP boundary before any call. It filters tool
discovery by caller role, blocks prompt-injection style tool-call inputs,
and emits sanitized Qal'a audit records for discovery and call decisions.

Usage (stdio):
    python -m agents.mcp.server

Required env:
    (none — Ollama runs locally with no auth)

Optional env:
    OLLAMA_BASE_URL         default: http://localhost:11434
    OLLAMA_MIHWAR_MODEL     default: deepseek-coder-v2:16b
    OLLAMA_BAYYINAH_MODEL   default: qwen2.5-coder:32b

Optional Aegis env:
    AEGIS_MCP_ROLE     default caller role (default: operator)
    AEGIS_TENANT_ID    tenant id written to Qal'a audit records
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from aegis_gateway import AegisAuditError, AegisMcpGateway


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "curlexai-agents"
SERVER_VERSION = "1.0.0"

TOOLS: list[dict[str, Any]] = [
    {
        "name": "mihwar_generate",
        "description": (
            "Senior coding architect (DeepSeek-Coder-V2-Instruct on Modal). "
            "Use for production code generation, multi-file refactoring, API design, "
            "and architecture work. Returns generated code plus rationale."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task description for the architect.",
                },
                "code": {
                    "type": "string",
                    "description": "Optional existing code to refactor or extend.",
                    "default": "",
                },
                "context": {
                    "type": "string",
                    "description": "Free-form context (file paths, constraints, etc.).",
                    "default": "",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "bayyinah_review",
        "description": (
            "Validation and security-review agent (Qwen2.5-Coder-32B-Instruct on Modal). "
            "Use for code review, security findings, tenant isolation checks, prompt injection "
            "surface review. Returns VERDICT (APPROVE/REQUEST_CHANGES/BLOCK) plus findings."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code or diff to review.",
                },
                "context": {
                    "type": "string",
                    "description": "Free-form context (PR description, intent, related files).",
                    "default": "",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "free_birds_review",
        "description": (
            "Free Birds swarm review pass: 8 aliased birds on Qwen2.5-Coder-32B "
            "(BAYYINAH_ENDPOINT). Each bird inspects a different angle: falcon "
            "(security/tenant), hawk (type/contract), shaheen (prompt-injection/secrets), "
            "kestrel (regression/coverage), osprey (dependency/supply-chain), harrier "
            "(modal/public-surface boundary), merlin (merge/conflict), saker "
            "(citations/legal). Returns an aggregated VERDICT plus per-bird findings."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code, diff, or PR body to review.",
                },
                "context": {
                    "type": "string",
                    "description": "Free-form context (intent, related files, prior findings).",
                    "default": "",
                },
                "focus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of bird ids to limit the pass (default: all 8).",
                    "default": [],
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "free_birds_design",
        "description": (
            "Free Birds swarm design pass: 4 aliased birds on DeepSeek-Coder-V2-Instruct "
            "(MIHWAR_ENDPOINT). owl (architecture/multi-file plan), raven (task "
            "decomposition/API contract), eagle (refactor/perf), phoenix (system design). "
            "Returns a plan, file list, and implementation outline."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task or feature description.",
                },
                "code": {
                    "type": "string",
                    "description": "Optional existing code to extend or refactor.",
                    "default": "",
                },
                "context": {
                    "type": "string",
                    "description": "Free-form context (constraints, related modules).",
                    "default": "",
                },
                "focus": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of bird ids to limit the pass (default: all 4).",
                    "default": [],
                },
            },
            "required": ["task"],
        },
    },
]

GATEWAY: AegisMcpGateway | None = None

FREE_BIRDS_REVIEW = [
    {"id": "falcon", "checks": ["security_review", "tenant_validation"]},
    {"id": "hawk", "checks": ["type_safety", "contract_validation"]},
    {"id": "shaheen", "checks": ["prompt_injection_surface", "secrets_leakage_scan"]},
    {"id": "kestrel", "checks": ["regression_check", "test_coverage_gap_detection"]},
    {"id": "osprey", "checks": ["dependency_risk_assessment", "supply_chain_check"]},
    {"id": "harrier", "checks": ["modal_boundary_check", "public_surface_audit"]},
    {"id": "merlin", "checks": ["merge_safety", "conflict_analysis"]},
    {"id": "saker", "checks": ["citation_validation", "legal_risk_review"]},
]

FREE_BIRDS_DESIGN = [
    {"id": "owl", "checks": ["architecture", "multi_file_planning"]},
    {"id": "raven", "checks": ["task_decomposition", "api_contract_design"]},
    {"id": "eagle", "checks": ["refactoring_with_behavioral_preservation", "performance_critical_implementation"]},
    {"id": "phoenix", "checks": ["complex_multi_file_feature_development", "system_design"]},
]


def _gateway() -> AegisMcpGateway:
    """Return the lazily initialized Aegis gateway instance."""

    global GATEWAY
    if GATEWAY is None:
        GATEWAY = AegisMcpGateway(TOOLS)
    return GATEWAY


def _filter_birds(pool: list[dict[str, Any]], focus: list[str]) -> list[dict[str, Any]]:
    if not focus:
        return pool
    allowed = {f.lower() for f in focus if isinstance(f, str)}
    selected = [b for b in pool if b["id"] in allowed]
    return selected or pool



def _enrich_arguments(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "free_birds_review":
        focus = arguments.pop("focus", []) or []
        birds = _filter_birds(FREE_BIRDS_REVIEW, focus)
        return {
            **arguments,
            "role": "swarm_review",
            "swarm": "free-birds",
            "birds": birds,
        }
    if tool_name == "free_birds_design":
        focus = arguments.pop("focus", []) or []
        birds = _filter_birds(FREE_BIRDS_DESIGN, focus)
        return {
            **arguments,
            "role": "swarm_design",
            "swarm": "free-birds",
            "birds": birds,
        }
    return arguments


_OLLAMA_MODEL_MAP: dict[str, tuple[str, str]] = {
    "mihwar_generate": ("OLLAMA_MIHWAR_MODEL", "deepseek-coder-v2:16b"),
    "free_birds_design": ("OLLAMA_MIHWAR_MODEL", "deepseek-coder-v2:16b"),
    "bayyinah_review": ("OLLAMA_BAYYINAH_MODEL", "qwen2.5-coder:32b"),
    "free_birds_review": ("OLLAMA_BAYYINAH_MODEL", "qwen2.5-coder:32b"),
}


def _ollama_model_for(tool_name: str) -> str:
    env_key, default = _OLLAMA_MODEL_MAP.get(tool_name, ("", "qwen2.5-coder:32b"))
    return os.environ.get(env_key, default) if env_key else default


def _format_swarm_section(enriched: dict[str, Any]) -> str:
    birds = enriched.get("birds", [])
    bird_ids = [b["id"] for b in birds]
    checks = [c for b in birds for c in b.get("checks", [])]
    return (
        f"Swarm role: {enriched.get('role', 'unknown')}\n"
        f"Birds: {', '.join(bird_ids)}\n"
        f"Checks: {', '.join(checks)}"
    )


def _build_prompt(enriched: dict[str, Any]) -> str:
    sections = {
        "task": enriched.get("task", ""),
        "code": enriched.get("code", ""),
        "context": enriched.get("context", ""),
    }
    parts = []
    if sections["task"]:
        parts.append(sections["task"])
    if sections["code"]:
        parts.append(f"Code:\n{sections['code']}")
    if sections["context"]:
        parts.append(f"Context:\n{sections['context']}")
    if enriched.get("birds"):
        parts.append(_format_swarm_section(enriched))
    return "\n\n".join(parts) if parts else ""


def _call_local_ollama(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    enriched = _enrich_arguments(tool_name, dict(arguments))
    model = _ollama_model_for(tool_name)
    prompt = _build_prompt(enriched)

    data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Local Ollama request failed for {tool_name}. "
            f"Ensure Ollama is running at {base_url}."
        ) from exc

    result = json.loads(body)
    return {"response": result.get("response", ""), "model": model, "provider": "local_ollama"}


def _send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def _result(request_id: Any, result: Any) -> None:
    _send({"jsonrpc": "2.0", "id": request_id, "result": result})


def _error(request_id: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def _handle(request: dict[str, Any]) -> None:
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {}) or {}
    if not isinstance(params, dict):
        params = {}

    if method == "initialize":
        _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
        return

    if method == "notifications/initialized":
        return

    if method == "tools/list":
        try:
            tools = _gateway().filter_tools(params, request_id)
        except AegisAuditError:
            _error(request_id, -32603, "Aegis audit failed for tool discovery.")
            return
        _result(request_id, {"tools": tools})
        return

    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        arguments = params.get("arguments", {}) or {}
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            decision = _gateway().authorize_tool_call(tool_name, arguments, params, request_id)
        except AegisAuditError:
            _result(
                request_id,
                {
                    "content": [{"type": "text", "text": "Error: Aegis audit failed."}],
                    "isError": True,
                },
            )
            return
        if not decision.allowed:
            _result(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Aegis MCP gateway blocked request ({decision.reason}).",
                        }
                    ],
                    "isError": True,
                },
            )
            return
        try:
            output = _call_local_ollama(tool_name, arguments)
        except Exception as exc:
            _result(
                request_id,
                {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            )
            return
        _result(
            request_id,
            {
                "content": [
                    {"type": "text", "text": json.dumps(output, ensure_ascii=False, indent=2)}
                ],
                "isError": False,
            },
        )
        return

    if method == "ping":
        _result(request_id, {})
        return

    _error(request_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            _handle(request)
        except Exception as exc:
            request_id = request.get("id") if isinstance(request, dict) else None
            _error(request_id, -32603, f"Internal error: {exc}")


if __name__ == "__main__":
    main()
