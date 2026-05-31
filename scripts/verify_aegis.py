#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Aegis final verification gate for CurLexAI/swarms.

This script performs local, evidence-oriented checks for the repository's
sovereign swarm controls. It is intentionally adapted to the current repository
layout instead of acting as a generic template:

* SAMA ingestion swarm agents and orchestrator must exist.
* Local inference adapters for Ollama and llama.cpp must exist and enforce
  sovereign/local URL validation.
* Router code must block when local providers are unavailable instead of falling
  through to external providers.
* The audit-chain components and SAMA audit integration must be present.
* Qdrant/vector indexing must remain an injected port rather than a hard-coded
  cloud dependency.
* Source files must not contain common literal credential patterns.
* The Python test suite must pass.

The gate does not claim runtime availability for services that are not started
inside CI. It verifies code-level controls and runs local tests only.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SWARM_DIR = REPO_ROOT / "sama_ingestion_swarm"
PROVIDERS_DIR = REPO_ROOT / "src" / "providers"
CORE_DIR = REPO_ROOT / "src" / "core"
TESTS_DIR = REPO_ROOT / "tests"

SKIP_SCAN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    ".venv-modal",
}

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI API key", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    ("GitHub personal access token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("GitHub fine-grained token", re.compile(r"github_pat_[A-Za-z0-9_]{80,}")),
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("static bearer token", re.compile(r"Bearer\s+(?!auth\b|header\b)[A-Za-z0-9_\-.]{24,}=*")),
    (
        "hard-coded password assignment",
        re.compile(r"password\s*=\s*[\"'][^\"'\n]{8,}[\"']", re.IGNORECASE),
    ),
)

EXTERNAL_AI_MARKERS = (
    "api.openai.com",
    "api.anthropic.com",
    "generativelanguage.googleapis.com",
    "vertexai.googleapis.com",
)


@dataclass(slots=True)
class GateState:
    """Mutable pass/fail counters for the Aegis gate."""

    passed: int = 0
    failed: int = 0

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        """Record and print one verification result.

        Args:
            name: Human-readable check name.
            condition: Whether the check passed.
            detail: Optional failure detail. It must not contain secrets.
        """

        if condition:
            print(f"✅ VERIFIED: {name}")
            self.passed += 1
            return
        suffix = f" — {detail}" if detail else ""
        print(f"❌ FAILED: {name}{suffix}")
        self.failed += 1


def read_text(path: Path) -> str:
    """Read a UTF-8 text file from the repository.

    Args:
        path: File path to read.

    Returns:
        File content as text.
    """

    return path.read_text(encoding="utf-8")


def has_any_marker(content: str, markers: Iterable[str]) -> bool:
    """Return whether content contains any case-insensitive marker."""

    lowered = content.lower()
    return any(marker.lower() in lowered for marker in markers)


def should_scan(path: Path) -> bool:
    """Return whether a Python file should be included in source scanning."""

    relative_parts = set(path.relative_to(REPO_ROOT).parts)
    return not bool(relative_parts & SKIP_SCAN_PARTS)


def python_source_files() -> list[Path]:
    """Return repository Python source files that are safe to scan."""

    return sorted(path for path in REPO_ROOT.rglob("*.py") if should_scan(path))


def run_pytest(timeout_seconds: int = 180) -> subprocess.CompletedProcess[str]:
    """Run the repository Python test suite.

    Args:
        timeout_seconds: Maximum test runtime before the gate fails.

    Returns:
        The completed pytest process.
    """

    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests/"],
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
        text=True,
        timeout=timeout_seconds,
    )


def print_section(title: str) -> None:
    """Print a stable section header."""

    print(f"\n--- {title} ---")


def verify_swarm_files(state: GateState) -> None:
    """Verify required SAMA swarm files exist."""

    print_section("1. SAMA swarm files")
    required = (
        SWARM_DIR / "agent_fetcher.py",
        SWARM_DIR / "agent_parser.py",
        SWARM_DIR / "agent_auditor.py",
        SWARM_DIR / "orchestrator.py",
    )
    for path in required:
        state.check(f"{path.relative_to(REPO_ROOT)} exists", path.is_file())


def verify_local_providers(state: GateState) -> None:
    """Verify local-provider adapters and external-provider lockout controls."""

    print_section("2. Local provider controls")
    provider_paths = (
        PROVIDERS_DIR / "local_llama_cpp.py",
        PROVIDERS_DIR / "local_ollama.py",
    )
    for path in provider_paths:
        state.check(f"{path.relative_to(REPO_ROOT)} exists", path.is_file())
        if not path.is_file():
            continue
        content = read_text(path)
        state.check(
            f"{path.name} enforces sovereign/local URL validation",
            "require_sovereign_local_url" in content,
            "provider adapter must validate local/internal base URLs",
        )
        state.check(
            f"{path.name} does not embed external AI API endpoints",
            not has_any_marker(content, EXTERNAL_AI_MARKERS),
            "external AI endpoint marker found",
        )
        state.check(
            f"{path.name} does not request external API keys",
            "api_key" not in content.lower() and "authorization: bearer" not in content.lower(),
            "external API-key style marker found",
        )


def verify_audit_chain_and_router(state: GateState) -> None:
    """Verify router blocking and audit-chain integration controls."""

    print_section("3. Router and audit-chain controls")
    required = (
        CORE_DIR / "classification.py",
        CORE_DIR / "model_router.py",
        CORE_DIR / "audited_router.py",
        CORE_DIR / "provider_interface.py",
    )
    for path in required:
        state.check(f"{path.relative_to(REPO_ROOT)} exists", path.is_file())

    router_path = CORE_DIR / "model_router.py"
    if router_path.is_file():
        content = read_text(router_path)
        state.check(
            "model_router blocks unavailable local providers",
            "BLOCKED_LOCAL_PROVIDER_UNAVAILABLE" in content,
            "missing explicit local-provider block reason",
        )
        state.check(
            "model_router does not embed external AI provider endpoints",
            not has_any_marker(content, EXTERNAL_AI_MARKERS),
            "external AI endpoint marker found",
        )
        state.check(
            "model_router does not read external AI API keys",
            "OPENAI_API_KEY" not in content and "ANTHROPIC_API_KEY" not in content,
            "external AI key marker found",
        )

    audited_path = CORE_DIR / "audited_router.py"
    if audited_path.is_file():
        content = read_text(audited_path)
        state.check(
            "audited_router exposes Qala audit adapter",
            "QalaAuditAdapter" in content and "verify_chain" in content,
            "audit adapter or chain verification missing",
        )

    swarm_init = SWARM_DIR / "__init__.py"
    if swarm_init.is_file():
        content = read_text(swarm_init)
        state.check(
            "SAMA swarm records and verifies audit events",
            "record_audit_event" in content and "verify_chain" in content,
            "SAMA audit-chain verification path missing",
        )


def verify_qdrant_port(state: GateState) -> None:
    """Verify Qdrant/vector indexing is represented as an injected port."""

    print_section("4. Qdrant/vector indexing boundary")
    auditor_path = SWARM_DIR / "agent_auditor.py"
    tests_path = TESTS_DIR / "test_sama_swarm.py"
    state.check("agent_auditor.py exists for vector boundary", auditor_path.is_file())
    if auditor_path.is_file():
        content = read_text(auditor_path)
        state.check(
            "auditor defines VectorIndexer port",
            "class VectorIndexer(Protocol)" in content and "upsert_article" in content,
            "Qdrant/vector indexer must remain injected behind a port",
        )
        state.check(
            "auditor accepts vector_indexer by dependency injection",
            "vector_indexer: VectorIndexer" in content,
            "missing injected vector indexer dependency",
        )
        state.check(
            "auditor does not hard-code Qdrant Cloud endpoint",
            "cloud.qdrant.io" not in content.lower(),
            "Qdrant Cloud endpoint marker found",
        )
    state.check("SAMA swarm tests include Qdrant/vector mock", tests_path.is_file())
    if tests_path.is_file():
        content = read_text(tests_path)
        state.check(
            "Qdrant/vector path has a test double",
            "FakeVectorIndexer" in content,
            "missing vector indexer mock coverage",
        )


def verify_secret_scan(state: GateState) -> None:
    """Scan Python source files for common literal secret patterns."""

    print_section("5. Python source secret scan")
    scanned = 0
    violations: list[str] = []
    for path in python_source_files():
        scanned += 1
        try:
            content = read_text(path)
        except UnicodeDecodeError as exc:
            violations.append(f"{path.relative_to(REPO_ROOT)}: unreadable UTF-8 ({exc})")
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(f"{path.relative_to(REPO_ROOT)}: {label}")

    for violation in violations:
        print(f"   ⚠️  {violation}")
    state.check(
        f"no literal secret patterns in {scanned} Python files",
        not violations,
        f"{len(violations)} potential violation(s)",
    )


def verify_environment_egress(state: GateState) -> None:
    """Verify external AI API keys are not present in the gate environment."""

    print_section("6. External AI egress environment")
    blocked_env_names = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "VERTEX_API_KEY",
    )
    for name in blocked_env_names:
        # Treat absent and empty-string as equivalent — an empty key grants no
        # external AI access, and CI runners may inject these as empty org vars.
        state.check(f"{name} is absent from environment", not os.environ.get(name))


def verify_pytest(state: GateState) -> None:
    """Run and report the Python test suite."""

    print_section("7. Python tests")
    try:
        result = run_pytest()
    except subprocess.TimeoutExpired as exc:
        state.check("python pytest suite", False, f"timed out after {exc.timeout} seconds")
        return
    except OSError as exc:
        state.check("python pytest suite", False, f"could not start pytest: {exc}")
        return

    if result.returncode == 0:
        tail = result.stdout.strip().splitlines()[-1:] or ["pytest completed"]
        print(f"   {tail[0]}")
        state.check("python pytest suite", True)
        return

    print("   pytest stdout tail:")
    print(indent_tail(result.stdout))
    print("   pytest stderr tail:")
    print(indent_tail(result.stderr))
    state.check("python pytest suite", False, f"exit code {result.returncode}")


def indent_tail(output: str, lines: int = 25) -> str:
    """Return an indented tail of command output for safe diagnostics."""

    tail = output.strip().splitlines()[-lines:]
    if not tail:
        return "      <empty>"
    return "\n".join(f"      {line}" for line in tail)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Aegis verification gate.

    Args:
        argv: Optional command-line arguments. Currently unused and accepted for
            future compatibility.

    Returns:
        Process exit code: ``0`` when all checks pass, otherwise ``1``.
    """

    del argv
    state = GateState()
    verify_swarm_files(state)
    verify_local_providers(state)
    verify_audit_chain_and_router(state)
    verify_qdrant_port(state)
    verify_secret_scan(state)
    verify_environment_egress(state)
    verify_pytest(state)

    print("\n" + "=" * 60)
    print(f"AEGIS RESULT: {state.passed} passed | {state.failed} failed")
    if state.failed == 0:
        print("🛡️  AEGIS VERIFIED: local repository gate passed with collected evidence.")
        return 0
    print("⚠️  AEGIS FAILED: fix the reported control or validation failures before merge.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
