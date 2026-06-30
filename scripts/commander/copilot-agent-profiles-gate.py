#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Validate GitHub Copilot custom agent profiles for Qarar control-plane safety."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REQUIRED_PROFILES = (
    "bayyinah.agent.md",
    "mihwar.agent.md",
    "qarar-platform-supervisor.agent.md",
    "free-birds.agent.md",
    "core-coding-swarm.agent.md",
)

FORBIDDEN_PATTERNS = (
    re.compile(r"(?i)\bprint\s+environment\s+variables\b"),
    re.compile(r"(?i)\bcommit\s+secrets\b"),
    re.compile(r"(?i)\bdeploy\s+production\s+automatically\b"),
    re.compile(r"(?i)\bexpose\s+raw\s+modal\b"),
    re.compile(r"(?i)\bdisable\s+aegis\b"),
    re.compile(r"(?i)\bdisable\s+secret[- ]scan\b"),
    re.compile(r"(?i)\bclaim\s+production\s+readiness\s+without\s+smoke\b"),
)

# Lines that contain these markers are negating the forbidden phrase, not instructing it.
NEGATION_MARKERS = (
    "do not",
    "don't",
    "never ",
    "avoid ",
    "reject ",
    "forbidden",
    "must not",
    "should not",
    "not allowed",
)

REQUIRED_PHRASES = (
    "VERIFIED",
    "INFERRED",
    "UNVERIFIED",
)

MIN_PROFILE_BYTES = 400


@dataclass(frozen=True)
class Finding:
    profile: str
    message: str


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") and "\n---\n" in text[4:]


def validate_profile(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    if not has_frontmatter(text):
        findings.append(Finding(path.name, "missing YAML frontmatter"))
        return findings

    parts = text.split("---", 2)
    if len(parts) < 3 or "description:" not in parts[1]:
        findings.append(Finding(path.name, "missing description in frontmatter"))

    if len(text.strip()) < MIN_PROFILE_BYTES:
        findings.append(Finding(path.name, "profile is too thin to encode useful operating policy"))

    for phrase in REQUIRED_PHRASES:
        if phrase not in text:
            findings.append(Finding(path.name, f"missing evidence label: {phrase}"))

    for pattern in FORBIDDEN_PATTERNS:
        for line in text.splitlines():
            if pattern.search(line):
                lower_line = line.lower()
                if not any(marker in lower_line for marker in NEGATION_MARKERS):
                    findings.append(Finding(path.name, f"forbidden instruction matched: {pattern.pattern}"))
                    break

    if "Do not" not in text and "Never" not in text:
        findings.append(Finding(path.name, "missing explicit safety constraints"))

    return findings


def main() -> int:
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    agents_dir = repo_root / ".github" / "agents"
    findings: list[Finding] = []

    if not agents_dir.exists():
        print("ERROR: .github/agents does not exist")
        return 1

    for filename in REQUIRED_PROFILES:
        path = agents_dir / filename
        if not path.exists():
            findings.append(Finding(filename, "required profile missing"))
            continue
        findings.extend(validate_profile(path))

    if findings:
        for finding in findings:
            print(f"ERROR: {finding.profile}: {finding.message}")
        return 1

    print("Copilot custom agent profiles gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
