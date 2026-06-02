#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Fail-closed secrets manifest validator (names only — never values).

Reads ``docs/launch-evidence/secrets-manifest.json`` and reports each declared
secret as SET or UNSET using **key membership only** (``name in os.environ``).
It never reads, prints, logs, or returns a secret value, length, or prefix.

Exit codes:
    0  -> all secrets required for the requested phase are SET
    1  -> at least one required secret is UNSET (fail closed)
    2  -> manifest missing or malformed

Usage:
    python3 scripts/check-secrets-manifest.py [--phase PHASE] [--all]

    --phase PHASE   Only enforce secrets whose "phase" matches PHASE
                    (others are reported but not enforced).
    --all           Enforce every required secret regardless of phase.
With no flag, every required secret is enforced (equivalent to --all).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MANIFEST = Path("docs/launch-evidence/secrets-manifest.json")


def load_manifest() -> list[dict[str, object]]:
    """Load and validate the manifest structure."""
    if not MANIFEST.is_file():
        print(f"[FAIL] manifest not found: {MANIFEST}")
        sys.exit(2)
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[FAIL] manifest is not valid JSON: {exc}")
        sys.exit(2)
    secrets = data.get("secrets")
    if not isinstance(secrets, list) or not secrets:
        print("[FAIL] manifest has no 'secrets' list")
        sys.exit(2)
    return secrets


def is_enforced(entry: dict[str, object], phase: str | None, enforce_all: bool) -> bool:
    """Return True when this required secret is in scope for enforcement."""
    if not bool(entry.get("required", False)):
        return False
    return enforce_all or phase is None or phase == str(entry.get("phase", ""))


def format_row(name: str, present: bool, entry: dict[str, object]) -> str:
    """Render a single presence row (SET/UNSET only — no value)."""
    state = "SET" if present else "UNSET"
    flag = "required" if bool(entry.get("required", False)) else "optional"
    return f"  {state:5s}  {name:24s} [{flag}, phase={entry.get('phase', '')}]"


def collect_missing(
    secrets: list[dict[str, object]], phase: str | None, enforce_all: bool
) -> list[str]:
    """Print presence rows and return the names of UNSET enforced secrets."""
    missing: list[str] = []
    print("SECRET PRESENCE (names only — values never read):")
    for entry in secrets:
        name = str(entry.get("name", ""))
        if not name:
            continue
        present = name in os.environ  # key membership only; value is never read
        print(format_row(name, present, entry))
        if is_enforced(entry, phase, enforce_all) and not present:
            missing.append(name)
    return missing


def main() -> int:
    """Run the fail-closed presence check."""
    parser = argparse.ArgumentParser(description="Validate secret presence (names only).")
    parser.add_argument("--phase", default=None, help="Only enforce this phase.")
    parser.add_argument("--all", action="store_true", help="Enforce all required secrets.")
    args = parser.parse_args()

    secrets = load_manifest()
    missing = collect_missing(secrets, args.phase, args.all)

    print("-" * 60)
    if missing:
        scope = args.phase if (args.phase and not args.all) else "all phases"
        print(f"[FAIL] {len(missing)} required secret(s) UNSET for {scope}: "
              f"{', '.join(sorted(missing))}")
        print("[RESULT] FAIL (fail-closed)")
        return 1

    print("[OK] all enforced required secrets are SET")
    print("[RESULT] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
