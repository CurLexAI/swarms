#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Fail-closed secrets manifest validator (redacted output — never values or names).

Reads ``docs/launch-evidence/secrets-manifest.json`` and reports each declared
secret as SET or UNSET using **key membership only** (``name in os.environ``).
To avoid logging anything that pattern-matches a secret, the output identifies
each secret by a stable redacted id (``entry-NN``, its 1-based manifest order),
never by name and never by value, length, or prefix. Map ids back to names via
``docs/launch-evidence/secrets-manifest.json``.

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


def entry_phases(entry: dict[str, object]) -> list[str]:
    """Return the manifest phases for an entry as normalized strings."""
    phase_value = entry.get("phase", "")
    if isinstance(phase_value, list):
        return [str(item) for item in phase_value]
    return [str(phase_value)]


def format_phases(entry: dict[str, object]) -> str:
    """Render phase metadata without exposing secret names or values."""
    return ",".join(entry_phases(entry))


def is_enforced(entry: dict[str, object], phase: str | None, enforce_all: bool) -> bool:
    """Return True when this required secret is in scope for enforcement."""
    if not bool(entry.get("required", False)):
        return False
    return enforce_all or phase is None or phase in entry_phases(entry)


def format_row(entry_id: str, state: str, entry: dict[str, object]) -> str:
    """Render a presence row from a redacted id and a constant state literal.

    Only the redacted ``entry_id``, a constant ``state`` ("SET"/"UNSET"), and
    the non-sensitive ``required``/``phase`` metadata are formatted. The secret
    name is never included, so nothing pattern-matching a secret can be logged.
    """
    flag = "required" if bool(entry.get("required", False)) else "optional"
    return f"  {state:5s}  {entry_id:12s} [{flag}, phase={format_phases(entry)}]"


def evaluate_entry(
    entry_id: str, entry: dict[str, object], phase: str | None, enforce_all: bool
) -> str | None:
    """Print one presence row; return the redacted id if UNSET and enforced.

    Presence is determined by key membership (``name in os.environ``) used
    purely as a control-flow condition; the name is read from the manifest but
    is never printed or returned.
    """
    name = str(entry.get("name", ""))
    if not name:
        return None
    if name in os.environ:  # membership only; the value is never read
        print(format_row(entry_id, "SET", entry))
        return None
    print(format_row(entry_id, "UNSET", entry))
    return entry_id if is_enforced(entry, phase, enforce_all) else None


def collect_missing(
    secrets: list[dict[str, object]], phase: str | None, enforce_all: bool
) -> list[str]:
    """Print presence rows and return the redacted ids of UNSET enforced secrets."""
    print("SECRET PRESENCE (redacted ids; names in docs/launch-evidence/secrets-manifest.json):")
    missing: list[str] = []
    for index, entry in enumerate(secrets, start=1):
        flagged = evaluate_entry(f"entry-{index:02d}", entry, phase, enforce_all)
        if flagged is not None:
            missing.append(flagged)
    return missing


def main() -> int:
    """Run the fail-closed presence check."""
    parser = argparse.ArgumentParser(description="Validate secret presence (redacted ids only).")
    parser.add_argument("--phase", default=None, help="Only enforce this phase.")
    parser.add_argument("--all", action="store_true", help="Enforce all required secrets.")
    args = parser.parse_args()

    secrets = load_manifest()
    missing = collect_missing(secrets, args.phase, args.all)

    print("-" * 60)
    if missing:
        scope = args.phase if (args.phase and not args.all) else "all phases"
        print(f"[FAIL] {len(missing)} required secret(s) UNSET for {scope}: "
              f"{', '.join(missing)}")
        print("[RESULT] FAIL (fail-closed)")
        return 1

    print("[OK] all enforced required secrets are SET")
    print("[RESULT] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
