"""MCP server exposing Mihwar and Bayyinah Modal endpoints as Copilot tools.

This server speaks the Model Context Protocol over stdio and forwards tool
calls to the Modal-hosted private agents. It reads endpoints and tokens from
environment variables that are provided by the Copilot environment / GitHub
Actions / local secrets.

Usage (stdio):
    python -m agents.mcp.server

Required env:
    MIHWAR_ENDPOINT
    BAYYINAH_ENDPOINT
    AGENT_API_TOKEN
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


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
]


def _endpoint_for(tool_name: str) -> tuple[str, str]:
    if tool_name == "mihwar_generate":
        return os.environ.get("MIHWAR_ENDPOINT", ""), "MIHWAR_ENDPOINT"
    if tool_name == "bayyinah_review":
        return os.environ.get("BAYYINAH_ENDPOINT", ""), "BAYYINAH_ENDPOINT"
    return "", ""


def _call_modal(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    endpoint, env_name = _endpoint_for(tool_name)
    token = os.environ.get("AGENT_API_TOKEN", "")
    if not endpoint:
        raise RuntimeError(f"{env_name} is not configured.")
    if not token:
        raise RuntimeError("AGENT_API_TOKEN is not configured.")

    payload = {"token": token, **arguments}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Modal endpoint request failed for {tool_name}.") from exc

    return json.loads(body)


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
        _result(request_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {}) or {}
        try:
            output = _call_modal(tool_name, arguments)
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
