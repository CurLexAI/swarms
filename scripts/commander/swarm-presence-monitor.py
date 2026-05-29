#!/usr/bin/env python3
"""Evidence-oriented presence monitor for CurLexAI swarms agents.

This replaces illustrative/mock presence checks with safe evidence collection.
It never prints token values. Default mode returns exit code 2 (HOLD) when
runtime evidence is missing; --strict treats HOLD as failure.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERIFIED = "VERIFIED"
HOLD = "HOLD"
FAILED = "FAILED"
SKIPPED = "SKIPPED_UNVERIFIED"

REQUIRED_STATIC_PATHS = (
    "README.md",
    "docs/decisions/ADR-0001-swarms-boundary.md",
    "scripts/verify_aegis.py",
    ".github/workflows/aegis-gate.yml",
    ".agents/mcp/modal-mcp/src/server.ts",
    ".agents/mcp/modal-mcp/src/config.ts",
    "src/services/unifiedAgentAdapter.ts",
    "src/services/unifiedAgentAdapter.js",
)


@dataclass(slots=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Report:
    generated_at: str
    repo: str
    strict: bool
    checks: list[Check]

    @property
    def summary(self) -> dict[str, int]:
        counts = {VERIFIED: 0, HOLD: 0, FAILED: 0, SKIPPED: 0}
        for check in self.checks:
            counts[check.status] = counts.get(check.status, 0) + 1
        return counts

    @property
    def exit_code(self) -> int:
        if self.summary[FAILED] > 0:
            return 1
        if self.strict and (self.summary[HOLD] + self.summary[SKIPPED]) > 0:
            return 1
        if (self.summary[HOLD] + self.summary[SKIPPED]) > 0:
            return 2
        return 0

    def to_json(self) -> str:
        return json.dumps(
            {
                "generatedAt": self.generated_at,
                "repo": self.repo,
                "strict": self.strict,
                "summary": self.summary,
                "checks": [check.__dict__ for check in self.checks],
                "exitCode": self.exit_code,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


class SwarmPresenceMonitor:
    def __init__(self, repo_root: Path, repo: str, no_network: bool, timeout_seconds: float = 8.0) -> None:
        self.repo_root = repo_root.resolve()
        self.repo = repo
        self.no_network = no_network
        self.timeout_seconds = timeout_seconds

    def run(self, strict: bool) -> Report:
        checks = [
            self.check_static_files(),
            self.check_static_gates(),
            self.check_git_worktree(),
            self.check_github_repo(),
            self.check_mcp_health(),
            self.check_entra_metadata(),
        ]
        return Report(datetime.now(timezone.utc).isoformat(), self.repo, strict, checks)

    def check_static_files(self) -> Check:
        missing = [path for path in REQUIRED_STATIC_PATHS if not (self.repo_root / path).exists()]
        if missing:
            return Check("static repository controls", FAILED, "required control files are missing", {"missing": missing})
        return Check("static repository controls", VERIFIED, "required control files exist", {"count": len(REQUIRED_STATIC_PATHS)})

    def check_static_gates(self) -> Check:
        gates = (
            "scripts/commander/adr-0001-boundary-gate.sh",
            "scripts/commander/modal-boundary-gate.sh",
            "scripts/commander/agent-presence-gate.sh",
            "scripts/verify_aegis.py",
        )
        missing = [path for path in gates if not (self.repo_root / path).exists()]
        if missing:
            return Check("static validation gates", FAILED, "one or more gates are missing", {"missing": missing})
        return Check("static validation gates", VERIFIED, "boundary, modal, agent-presence, and aegis gates are present")

    def check_git_worktree(self) -> Check:
        if not (self.repo_root / ".git").exists():
            return Check("git worktree identity", HOLD, "not running inside a Git checkout")
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=self.repo_root,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip() == "true":
            return Check("git worktree identity", VERIFIED, "running inside a Git worktree")
        return Check("git worktree identity", FAILED, "git did not confirm a worktree", {"stderr": safe_tail(result.stderr)})

    def check_github_repo(self) -> Check:
        if self.no_network:
            return Check("GitHub repository metadata", SKIPPED, "network checks disabled")
        token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not token:
            return Check("GitHub repository metadata", HOLD, "GITHUB_TOKEN/GH_TOKEN not configured")
        response = request_json(f"https://api.github.com/repos/{self.repo}", {"Authorization": f"Bearer {token}"}, self.timeout_seconds)
        if not response["ok"]:
            return Check("GitHub repository metadata", FAILED, "GitHub API request failed", scrub(response))
        payload = response.get("json", {})
        if not isinstance(payload, Mapping):
            return Check("GitHub repository metadata", FAILED, "GitHub API response was not an object")
        return Check(
            "GitHub repository metadata",
            VERIFIED,
            "repository metadata fetched",
            {"fullName": payload.get("full_name"), "private": payload.get("private"), "defaultBranch": payload.get("default_branch")},
        )

    def check_mcp_health(self) -> Check:
        if self.no_network:
            return Check("MCP health", SKIPPED, "network checks disabled")
        url = os.getenv("MCP_SERVER_URL") or os.getenv("MCP_HEALTH_URL")
        if not url:
            return Check("MCP health", HOLD, "MCP_SERVER_URL/MCP_HEALTH_URL not configured")
        response = request_json(url, {}, self.timeout_seconds)
        if response["ok"]:
            return Check("MCP health", VERIFIED, "MCP endpoint responded", {"url": redact_url(url), "statusCode": response.get("statusCode")})
        return Check("MCP health", FAILED, "MCP endpoint failed", {"url": redact_url(url), **scrub(response)})

    def check_entra_metadata(self) -> Check:
        if self.no_network:
            return Check("Microsoft Entra metadata", SKIPPED, "network checks disabled")
        tenant_id = os.getenv("ENTRA_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
        if not tenant_id:
            return Check("Microsoft Entra metadata", HOLD, "ENTRA_TENANT_ID/AZURE_TENANT_ID not configured")
        url = f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration"
        response = request_json(url, {}, self.timeout_seconds)
        if response["ok"]:
            return Check("Microsoft Entra metadata", VERIFIED, "tenant OIDC metadata reachable", {"tenantConfigured": True})
        return Check("Microsoft Entra metadata", FAILED, "tenant metadata request failed", scrub(response))


def request_json(url: str, headers: Mapping[str, str], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", **headers})
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            raw = response.read(512_000).decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            return {"ok": 200 <= response.status < 300, "statusCode": response.status, "json": parsed}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "statusCode": exc.code, "error": safe_tail(str(exc.reason))}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": safe_tail(str(exc.reason))}
    except TimeoutError:
        return {"ok": False, "error": "timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "non-json response"}


def scrub(value: Mapping[str, Any]) -> dict[str, Any]:
    blocked = {"token", "authorization", "secret", "password"}
    return {key: val for key, val in value.items() if all(part not in key.lower() for part in blocked)}


def redact_url(url: str) -> str:
    return url.split("?", 1)[0]


def safe_tail(value: str, limit: int = 240) -> str:
    return value.replace("\n", " ")[-limit:]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify swarms agent runtime presence evidence.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--repo", default="CurLexAI/swarms")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--output", choices=("json", "text"), default="json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = SwarmPresenceMonitor(Path(args.repo_root), args.repo, args.no_network).run(strict=args.strict)
    if args.output == "json":
        print(report.to_json())
    else:
        print(f"Swarm presence report: {report.repo} {report.summary}")
        for check in report.checks:
            print(f"- {check.status}: {check.name} — {check.detail}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
