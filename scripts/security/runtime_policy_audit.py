# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
Runtime policy audit — static gate for high-risk runtime patterns.
==================================================================
Distinct from `scripts/security/static_audit.py` (which scans for committed
secrets). This gate flags reintroduction of dangerous runtime constructs that
the agent hardening closed:

* unguarded `trust_remote_code=True` (supply-chain RCE on model load)
* admin tokens accepted from query strings
* CORS wildcard combined with credentials
* unpinned GitHub Actions
* Qdrant API-key requirement weakened in runtime docs/config
* the legacy shared endpoint bearer token

Findings carry a severity and a `blocking` flag:

* BLOCKING findings (the first three above) exit non-zero — these are clean in
  the current tree and must stay clean.
* ADVISORY findings (the last three) are printed for visibility but do NOT fail
  the gate, because the repo carries pre-existing, separately-tracked instances
  (e.g. ~50 unpinned third-party actions, historical ADR references to the
  shared token). Pin/remediation of those is tracked as its own work.

Usage:
    python3 scripts/security/runtime_policy_audit.py [relative-root]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Generator
from typing import Final


@dataclass(frozen=True)
class Check:
    severity: str
    blocking: bool
    pattern: re.Pattern[str]
    message: str


CHECKS: Final[list[Check]] = [
    Check(
        "CRITICAL",
        True,
        re.compile(r"trust_remote_code\s*=\s*True"),
        "trust_remote_code=True is forbidden unless guarded by runtime_security.py",
    ),
    Check(
        "CRITICAL",
        True,
        re.compile(r"admin[_-]?token.*(?:query|params|get\()", re.IGNORECASE),
        "admin token must not be accepted through query string",
    ),
    Check(
        "HIGH",
        True,
        re.compile(
            r"Access-Control-Allow-Origin['\"]?\s*[:=]\s*['\"]\*['\"].{0,200}credentials",
            re.IGNORECASE | re.DOTALL,
        ),
        "CORS wildcard with credentials is forbidden",
    ),
    Check(
        "HIGH",
        False,
        re.compile(r"uses:\s*[^@\s]+@(?:main|master|latest|v\d+)\b", re.IGNORECASE),
        "GitHub Actions should be pinned to immutable commit SHAs",
    ),
    Check(
        "HIGH",
        False,
        re.compile("QDRANT" + r"_API_KEY.*optional", re.IGNORECASE),
        "Qdrant API key must not be documented as optional without local/dev private-network break-glass scope",
    ),
    Check(
        "MEDIUM",
        False,
        re.compile("AGENT" + r"_API_TOKEN.*shared", re.IGNORECASE),
        "Shared endpoint bearer token should be replaced with endpoint-specific tokens",
    ),
]

SKIP_DIRS: Final[set[str]] = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
}
# Code/config surfaces only — docs are excluded so historical narrative in ADRs
# does not produce noise. This file is skipped so its own patterns don't match.
SCAN_EXTS: Final[set[str]] = {".py", ".yml", ".yaml", ".js", ".ts", ".tsx", ".json"}
SELF = Path(__file__).resolve()


def _iter_files(root: Path) -> Generator[Path, None, None]:
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file() or path.suffix not in SCAN_EXTS:
            continue
        if path.resolve() == SELF:
            continue
        yield path


def main() -> int:
    base_dir = Path.cwd().resolve()
    raw_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if raw_root.is_absolute():
        print(f"Audit target must be a relative path: {raw_root}", file=sys.stderr)
        return 2
    root = (base_dir / raw_root).resolve()
    try:
        root.relative_to(base_dir)
    except ValueError:
        print(f"Audit target escapes allowed base directory: {raw_root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"Audit target is not a directory: {root}", file=sys.stderr)
        return 2

    blocking: list[str] = []
    advisory: list[str] = []
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(root)
        for check in CHECKS:
            for match in check.pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                entry = f"{check.severity}: {rel}:{line}: {check.message}"
                (blocking if check.blocking else advisory).append(entry)

    if advisory:
        print("ADVISORY FINDINGS (non-blocking):")
        for finding in advisory:
            print(f"  {finding}")
    if blocking:
        print("BLOCKING FINDINGS:")
        for finding in blocking:
            print(f"  {finding}")
        return 1
    print("RUNTIME POLICY AUDIT: no blocking findings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
