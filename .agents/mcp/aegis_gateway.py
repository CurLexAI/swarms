# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Aegis gateway controls for the CurLexAI MCP agent server.

The gateway is intentionally local-only and dependency-free. It sits at the
MCP boundary before tool discovery or tool execution reaches Modal-hosted
agents. It provides the first Aegis layer from the May 28 security
architecture:

* role-based filtering for ``tools/list``;
* prompt-injection style inspection for ``tools/call`` arguments;
* sanitized, hash-chained request audit records through Qal'a.

No raw tool arguments are written to the audit sink. Payloads contain only
metadata, field paths, lengths, hashes, role decisions, and rule ids.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol, cast


_DEFAULT_ROLE: Final[str] = "operator"
_DEFAULT_TENANT: Final[str] = "system"
_AUDIT_EVENT: Final[str] = "policy_decision"

_ROLE_TOOL_ALLOWLIST: Final[dict[str, frozenset[str]]] = {
    "observer": frozenset({"bayyinah_review", "free_birds_review"}),
    "reviewer": frozenset({"bayyinah_review", "free_birds_review"}),
    "architect": frozenset(
        {
            "mihwar_generate",
            "bayyinah_review",
            "free_birds_review",
            "free_birds_design",
        }
    ),
    "operator": frozenset(
        {
            "mihwar_generate",
            "bayyinah_review",
            "free_birds_review",
            "free_birds_design",
        }
    ),
    "admin": frozenset(
        {
            "mihwar_generate",
            "bayyinah_review",
            "free_birds_review",
            "free_birds_design",
        }
    ),
}

_PROMPT_INJECTION_RULES: Final[tuple[tuple[str, str, str, re.Pattern[str]], ...]] = (
    (
        "aegis.prompt.ignore_previous",
        "Instruction override attempt",
        "HIGH",
        re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b", re.I),
    ),
    (
        "aegis.prompt.reveal_hidden_prompt",
        "Hidden prompt disclosure attempt",
        "HIGH",
        re.compile(r"\b(?:reveal|print|show|dump)\s+(?:the\s+)?(?:system|developer)\s+prompt\b", re.I),
    ),
    (
        "aegis.prompt.secret_exfiltration",
        "Secret exfiltration attempt",
        "CRITICAL",
        re.compile(r"\b(?:exfiltrate|print|dump|show|reveal)\s+(?:secrets?|tokens?|environment|env|api[_-]?keys?)\b", re.I),
    ),
    (
        "aegis.prompt.disable_safety",
        "Safety control bypass attempt",
        "HIGH",
        re.compile(r"\b(?:disable|bypass|turn\s+off)\s+(?:safety|policy|guardrails?|aegis|filters?)\b", re.I),
    ),
    (
        "aegis.prompt.jailbreak_persona",
        "Jailbreak persona attempt",
        "HIGH",
        re.compile(r"\bact\s+as\s+(?:dan|jailbreak|unrestricted|uncensored)\b", re.I),
    ),
)

_BLOCKING_SEVERITIES: Final[frozenset[str]] = frozenset({"HIGH", "CRITICAL"})
_MAX_INSPECTED_STRING_CHARS: Final[int] = 20_000


class AuditSink(Protocol):
    """Port for append-only audit sinks used by the gateway."""

    def append(
        self,
        *,
        event: str,
        trace_id: str,
        span_id: str,
        tenant_id: str,
        payload: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> Any:
        """Append an audit record and return the sink-specific result.

        Args:
            event: Qal'a audit event name.
            trace_id: Request trace identifier.
            span_id: Gateway span identifier.
            tenant_id: Tenant boundary identifier.
            payload: Sanitized event payload.
            occurred_at: Optional caller-provided timestamp.

        Returns:
            Sink-specific append result exposing an ``ok`` attribute.
        """


@dataclass(frozen=True)
class AegisFinding:
    """Sanitized finding produced while inspecting tool-call arguments."""

    rule_id: str
    title: str
    severity: str
    field_path: str


@dataclass(frozen=True)
class AegisDecision:
    """Authorization decision for an MCP tool call."""

    allowed: bool
    role: str
    reason: str
    findings: tuple[AegisFinding, ...]


class AegisAuditError(RuntimeError):
    """Raised when the gateway cannot emit a required audit record."""


class AegisMcpGateway:
    """MCP boundary guard for tool discovery and tool-call requests.

    Args:
        tools: Full server-side MCP tool definitions.
        audit_sink: Optional audit sink for tests or alternate adapters.
        role_policy: Optional injected role-to-tool allowlist.
        tenant_id: Optional tenant id for audit records.
        default_role: Optional role used when request metadata is absent.
    """

    def __init__(
        self,
        tools: Sequence[Mapping[str, Any]],
        *,
        audit_sink: AuditSink | None = None,
        role_policy: Mapping[str, frozenset[str]] | None = None,
        tenant_id: str | None = None,
        default_role: str | None = None,
    ) -> None:
        self._tools = tuple(dict(tool) for tool in tools)
        self._known_tools = frozenset(
            str(tool.get("name")) for tool in self._tools if isinstance(tool.get("name"), str)
        )
        self._role_policy = dict(role_policy or _ROLE_TOOL_ALLOWLIST)
        self._audit_sink = audit_sink if audit_sink is not None else _load_qala_audit_sink()()
        self._tenant_id = _clean_identifier(
            tenant_id or os.environ.get("AEGIS_TENANT_ID") or _DEFAULT_TENANT,
            fallback=_DEFAULT_TENANT,
        )
        self._default_role = _normalize_role(
            default_role or os.environ.get("AEGIS_MCP_ROLE") or _DEFAULT_ROLE
        )

    def filter_tools(self, params: Mapping[str, Any], request_id: Any) -> list[dict[str, Any]]:
        """Return the role-filtered tool list and audit the discovery request.

        Args:
            params: JSON-RPC request params for ``tools/list``.
            request_id: JSON-RPC request id.

        Returns:
            MCP tool definitions allowed for the resolved role.

        Raises:
            AegisAuditError: If the discovery audit record cannot be written.
        """

        role = self.resolve_role(params)
        allowed = self._allowed_tools_for_role(role)
        filtered = [dict(tool) for tool in self._tools if str(tool.get("name")) in allowed]
        self._audit(
            action="mcp_tool_discovery",
            request_id=request_id,
            role=role,
            payload={
                "allowed_tools": sorted(allowed),
                "discovered_tools": [str(tool.get("name")) for tool in filtered],
                "tool_count": len(filtered),
            },
        )
        return filtered

    def authorize_tool_call(
        self,
        tool_name: str,
        arguments: Mapping[str, Any],
        params: Mapping[str, Any],
        request_id: Any,
    ) -> AegisDecision:
        """Authorize an MCP tool call and emit a sanitized audit record.

        Args:
            tool_name: MCP tool name requested by the client.
            arguments: Tool-call arguments from the MCP request.
            params: JSON-RPC request params for ``tools/call``.
            request_id: JSON-RPC request id.

        Returns:
            Authorization decision. A denied decision must not be forwarded.

        Raises:
            AegisAuditError: If the call audit record cannot be written.
        """

        role = self.resolve_role(params)
        findings = inspect_prompt_injection(arguments)
        allowed_tools = self._allowed_tools_for_role(role)
        argument_summary = summarize_arguments(arguments)

        if tool_name not in self._known_tools:
            decision = AegisDecision(False, role, "unknown_tool", findings)
        elif tool_name not in allowed_tools:
            decision = AegisDecision(False, role, "role_not_allowed", findings)
        elif any(finding.severity in _BLOCKING_SEVERITIES for finding in findings):
            decision = AegisDecision(False, role, "prompt_injection_blocked", findings)
        else:
            decision = AegisDecision(True, role, "approved", findings)

        self._audit(
            action="mcp_tool_call_approved" if decision.allowed else "mcp_tool_call_blocked",
            request_id=request_id,
            role=role,
            payload={
                "tool_name": tool_name,
                "decision": decision.reason,
                "argument_keys": argument_summary["argument_keys"],
                "argument_size_bytes": argument_summary["argument_size_bytes"],
                "argument_sha256": argument_summary["argument_sha256"],
                "findings": [finding.__dict__ for finding in findings],
            },
        )
        return decision

    def resolve_role(self, params: Mapping[str, Any]) -> str:
        """Resolve the caller role from MCP metadata or server defaults.

        Args:
            params: JSON-RPC request params.

        Returns:
            Normalized role. Unknown roles degrade to ``observer``.
        """

        candidates: list[Any] = [params.get("role"), params.get("aegis_role")]
        meta = params.get("_meta")
        if isinstance(meta, Mapping):
            candidates.extend([meta.get("role"), meta.get("aegis_role")])
            aegis_meta = meta.get("aegis")
            if isinstance(aegis_meta, Mapping):
                candidates.append(aegis_meta.get("role"))

        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return _normalize_role(candidate, known_roles=frozenset(self._role_policy))
        return _normalize_role(self._default_role, known_roles=frozenset(self._role_policy))

    def _allowed_tools_for_role(self, role: str) -> frozenset[str]:
        return self._role_policy.get(role, self._role_policy["observer"])

    def _audit(
        self,
        *,
        action: str,
        request_id: Any,
        role: str,
        payload: Mapping[str, Any],
    ) -> None:
        trace_id = str(uuid.uuid4())
        append_result = self._audit_sink.append(
            event=_AUDIT_EVENT,
            trace_id=trace_id,
            span_id=f"aegis_mcp.{action}",
            tenant_id=self._tenant_id,
            payload={
                "action": action,
                "request_id": str(request_id),
                "role": role,
                **dict(payload),
            },
        )
        if getattr(append_result, "ok", False) is not True:
            error = getattr(append_result, "error", "AUDIT_WRITE_FAILED")
            raise AegisAuditError(f"{error}: unable to write Aegis MCP audit record")


def inspect_prompt_injection(arguments: Mapping[str, Any]) -> tuple[AegisFinding, ...]:
    """Inspect tool-call arguments for prompt-injection style abuse.

    Args:
        arguments: Tool-call arguments from a JSON-RPC request.

    Returns:
        Sanitized findings containing rule ids and field paths only.
    """

    findings: list[AegisFinding] = []
    for field_path, value in _iter_string_values(arguments):
        inspected = value[:_MAX_INSPECTED_STRING_CHARS]
        for rule_id, title, severity, pattern in _PROMPT_INJECTION_RULES:
            if pattern.search(inspected):
                findings.append(
                    AegisFinding(
                        rule_id=rule_id,
                        title=title,
                        severity=severity,
                        field_path=field_path,
                    )
                )
                break
    return tuple(findings)


def summarize_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Create a sanitized metadata summary for tool-call arguments.

    Args:
        arguments: Tool-call arguments from a JSON-RPC request.

    Returns:
        Dictionary with argument keys, UTF-8 byte size, and SHA-256 hash.
    """

    encoded = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str).encode(
        "utf-8"
    )
    return {
        "argument_keys": sorted(str(key) for key in arguments.keys()),
        "argument_size_bytes": len(encoded),
        "argument_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _iter_string_values(value: Any, path: str = "$") -> tuple[tuple[str, str], ...]:
    if isinstance(value, str):
        return ((path, value),)
    if isinstance(value, Mapping):
        items: list[tuple[str, str]] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if isinstance(key, str) else f"{path}.*"
            items.extend(_iter_string_values(child, child_path))
        return tuple(items)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        items = []
        for index, child in enumerate(value):
            items.extend(_iter_string_values(child, f"{path}[{index}]"))
        return tuple(items)
    return ()


def _normalize_role(role: str, *, known_roles: frozenset[str] | None = None) -> str:
    normalized = re.sub(r"[^a-z0-9_-]", "", role.strip().lower())
    if not normalized:
        return "observer"
    if known_roles is not None and normalized not in known_roles:
        return "observer"
    return normalized


def _clean_identifier(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]", "-", value.strip())
    return cleaned or fallback


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_qala_audit_sink() -> type[AuditSink]:
    sink_path = _repo_root() / ".agents" / "validators" / "qala_audit_sink.py"
    spec = importlib.util.spec_from_file_location("_aegis_qala_audit_sink", sink_path)
    if spec is None or spec.loader is None:
        raise AegisAuditError("Qala audit sink loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    sink_cls = getattr(module, "QalaAuditSink", None)
    if sink_cls is None:
        raise AegisAuditError("QalaAuditSink unavailable")
    return cast(type[AuditSink], sink_cls)


__all__ = [
    "AegisAuditError",
    "AegisDecision",
    "AegisFinding",
    "AegisMcpGateway",
    "inspect_prompt_injection",
    "summarize_arguments",
]
