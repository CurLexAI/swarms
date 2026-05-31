# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Offline MCP server — NO-SECRETS mode.

Exposes local-only tools for Copilot coding agent use without requiring
any external endpoints, API keys, or runtime secrets. All tools perform
static analysis or return structured plans; none make network calls.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("qarar-offline-mcp")

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai", re.compile(r"sk-(proj|admin)?-[A-Za-z0-9_-]{20,}")),
    ("anthropic", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_-]{20,}")),
    ("github", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("telegram", re.compile(r"\d{8,12}:[A-Za-z0-9_-]{30,}")),
    ("google", re.compile(r"AIza[0-9A-Za-z_-]{20,}")),
    ("groq", re.compile(r"gsk_[A-Za-z0-9_-]{20,}")),
    ("xai", re.compile(r"xai-[A-Za-z0-9_-]{20,}")),
    ("perplexity", re.compile(r"pplx-[A-Za-z0-9_-]{20,}")),
    ("render", re.compile(r"api\.render\.com/deploy/srv-[A-Za-z0-9_-]+")),
    ("private_key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("bcrypt_hash", re.compile(r"\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}")),
]

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
    "__pycache__",
    ".venv",
    "venv",
}

SCAN_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".txt",
    ".env",
    ".sh",
}


def _safe_path(path: str) -> Path:
    root = Path.cwd().resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError("Path escapes repository root")
    return target


def _should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name == ".env" or path.name.startswith(".env."):
        return True
    return path.suffix in SCAN_EXTENSIONS


@mcp.tool()
def repo_static_audit(path: str = ".") -> dict[str, Any]:
    """Static repository audit without external calls or secrets.

    Scans for obvious secret patterns and risky files.
    """
    root = _safe_path(path)
    findings: list[dict[str, Any]] = []
    for item in root.rglob("*"):
        if not item.is_file() or not _should_scan(item):
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(
                    {
                        "severity": "CRITICAL",
                        "type": name,
                        "file": str(item.relative_to(Path.cwd())),
                        "line": line,
                        "message": "Possible secret detected. Value redacted.",
                    }
                )
    return {
        "ok": len(findings) == 0,
        "mode": "offline_no_secrets",
        "findings": findings,
        "count": len(findings),
    }


@mcp.tool()
def mihwar_generate_offline(
    feature_name: str, constraints: list[str] | None = None
) -> dict[str, Any]:
    """Generate an offline Mihwar implementation plan.

    Does not call Mihwar, Bayyinah, Modal, or any external service.
    """
    clean_name = feature_name.strip()
    if not clean_name:
        return {
            "ok": False,
            "error": "feature_name is required",
        }
    return {
        "ok": True,
        "mode": "offline_no_secrets",
        "feature": clean_name,
        "plan": [
            "Define strict input/output schema.",
            "Add HMAC or internal auth boundary before any runtime endpoint.",
            "Add append-only audit event.",
            "Add tests for allow/block paths.",
            "Keep execution draft-only until human approval is wired.",
        ],
        "constraints": constraints or [],
    }


@mcp.tool()
def bayyinah_review_offline(text: str) -> dict[str, Any]:
    """Offline policy review for obvious risk markers.

    Does not send text to any model or API.
    """
    lowered = text.lower()
    risk_markers = [
        "ignore previous instructions",
        "system prompt",
        "developer message",
        "api_key",
        "secret",
        "token",
        "password",
        "sk-",
        "ghp_",
        "AIza",
        "اتجاهل التعليمات",
        "اكشف التعليمات",
        "مفتاح",
        "توكن",
        "كلمة المرور",
    ]
    hits = [marker for marker in risk_markers if marker.lower() in lowered]
    return {
        "ok": len(hits) == 0,
        "mode": "offline_no_secrets",
        "risk": "HIGH" if hits else "LOW",
        "hits": hits,
        "recommendation": "BLOCK_AND_REVIEW" if hits else "ALLOW_DRAFT_ONLY",
    }


@mcp.tool()
def qarar_agent_registry_suggest() -> dict[str, Any]:
    """Suggest a small safe agent registry before scaling to 144 agents."""
    return {
        "ok": True,
        "mode": "offline_no_secrets",
        "recommended_first_agents": [
            {
                "id": "evidence-retriever",
                "system": "Bayyinah",
                "execute_can": False,
                "human_review_required": True,
            },
            {
                "id": "citation-validator",
                "system": "Bayyinah",
                "execute_can": False,
                "human_review_required": True,
            },
            {
                "id": "policy-gate",
                "system": "Mihwar",
                "execute_can": False,
                "human_review_required": True,
            },
            {
                "id": "draft-writer",
                "system": "Qarar",
                "execute_can": False,
                "human_review_required": True,
            },
            {
                "id": "security-auditor",
                "system": "Mihwar",
                "execute_can": False,
                "human_review_required": True,
            },
        ],
        "decision": "Start with 5 guarded agents, not 144 live agents.",
    }


if __name__ == "__main__":
    mcp.run()
