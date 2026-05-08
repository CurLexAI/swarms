"""
CurLexAI Agent Invoker — CLI
=============================
Call Mihwar or Bayyinah from the terminal without writing Python.

Usage examples:
    # Ask Mihwar to generate code
    python .agents/invoke.py mihwar "Write a FastAPI endpoint for user login"

    # Ask Bayyinah to review a file
    python .agents/invoke.py bayyinah --file src/auth.py

    # Ask Bayyinah to review a git diff
    python .agents/invoke.py bayyinah --diff

    # Full pipeline: Mihwar generates, Bayyinah reviews
    python .agents/invoke.py pipeline "Add rate limiting to the API"

    # Show agent config
    python .agents/invoke.py info

Requirements:
    pip install modal pyyaml
    modal token set --token-id ... --token-secret ...
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_yaml_spec = importlib.util.find_spec("yaml")
yaml = importlib.import_module("yaml") if _yaml_spec else None

CONFIG_PATH = Path(__file__).parent / "config" / "agents.yaml"
MODAL_APP_PATH = Path(__file__).parent / "modal_app.py"


# ── Config loader ──────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        _die(f"Config not found: {CONFIG_PATH}")
    config_text = CONFIG_PATH.read_text()
    if yaml is not None:
        return yaml.safe_load(config_text)
    return _load_minimal_agents_yaml(config_text)


def _load_minimal_agents_yaml(config_text: str) -> dict[str, Any]:
    """Parse this repository's agent config when PyYAML is unavailable.

    The fallback intentionally supports only the simple mapping/list/literal-block
    subset used by .agents/config/agents.yaml so `python .agents/invoke.py info`
    can run in a clean checkout without installing deployment dependencies.
    """

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    skip_literal_parent_indent: int | None = None
    lines = config_text.splitlines()

    for index, raw_line in enumerate(lines):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if skip_literal_parent_indent is not None:
            if indent > skip_literal_parent_indent:
                continue
            skip_literal_parent_indent = None

        line = _strip_yaml_comment(raw_line.strip())
        if not line:
            continue

        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Unsupported YAML list placement in agent config")
            parent.append(_parse_yaml_scalar(line[2:].strip()))
            continue

        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not isinstance(parent, dict):
            raise ValueError("Unsupported YAML mapping placement in agent config")

        if raw_value == "|":
            parent[key] = ""
            skip_literal_parent_indent = indent
        elif raw_value == "":
            next_significant = _next_significant_line(lines, index)
            if next_significant is None:
                child = {}
            else:
                _, next_indent, next_line = next_significant
                if next_indent <= indent:
                    child = {}
                else:
                    child = [] if next_line.startswith("- ") else {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_yaml_scalar(raw_value)

    return root


def _next_significant_line(lines: list[str], start_index: int) -> tuple[int, int, str] | None:
    for i in range(start_index + 1, len(lines)):
        raw_line = lines[i]
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = _strip_yaml_comment(raw_line.strip())
        if not line:
            continue
        return i, indent, line
    return None


def _strip_yaml_comment(value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value


def _parse_yaml_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.isdigit():
        return int(value)
    return value


# ── Modal call helpers ─────────────────────────────────────────────────────

def call_mihwar(task: str, context_files: dict[str, str] | None = None) -> dict:
    """
    Call Mihwar via Modal. Returns the full result dict.
    Uses modal run for simple calls, modal call for production endpoints.
    """
    _check_modal()

    cmd = [
        "modal", "run",
        str(MODAL_APP_PATH) + "::MihwarAgent.review_and_generate",
        "--task", task,
    ]
    if context_files:
        cmd += ["--context-files", json.dumps(context_files)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        _die(f"Mihwar call failed:\n{result.stderr}")

    return {"response": result.stdout, "agent": "mihwar"}


def call_bayyinah_file(file_path: str) -> dict:
    """Review a single file with Bayyinah."""
    _check_modal()

    path = Path(file_path)
    if not path.exists():
        _die(f"File not found: {file_path}")

    code = path.read_text()
    return _call_bayyinah_code(code, context=f"Reviewing file: {file_path}")


def call_bayyinah_diff() -> dict:
    """Review the current git diff with Bayyinah."""
    _check_modal()

    result = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True, text=True,
    )
    diff = result.stdout
    if not diff.strip():
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True,
        )
        diff = result.stdout

    if not diff.strip():
        print("No diff found (nothing staged or changed).")
        sys.exit(0)

    return _call_bayyinah_code(diff, context="Reviewing git diff")


def _call_bayyinah_code(code: str, context: str = "") -> dict:
    result = subprocess.run(
        [
            "modal", "run",
            str(MODAL_APP_PATH) + "::BayyinahAgent.review",
            "--code-or-diff", code,
            "--context", context,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        _die(f"Bayyinah call failed:\n{result.stderr}")

    verdict = "REQUEST_CHANGES"
    if "VERDICT: APPROVE" in result.stdout.upper():
        verdict = "APPROVE"

    return {
        "agent": "bayyinah",
        "verdict": verdict,
        "report": result.stdout,
    }


def run_pipeline(task: str) -> None:
    """
    Full Mihwar → Bayyinah pipeline.
    Mihwar generates code, Bayyinah reviews it.
    Repeats up to max_revision_cycles if Bayyinah requests changes.
    """
    config = load_config()
    max_cycles = config.get("collaboration", {}).get("max_revision_cycles", 3)

    print(f"\n{'='*60}")
    print(f"PIPELINE: {task}")
    print(f"{'='*60}")

    current_task = task
    for cycle in range(1, max_cycles + 1):
        print(f"\n── Cycle {cycle}/{max_cycles} ──────────────────────────")

        print("\n[1/2] Mihwar generating...")
        mihwar_result = call_mihwar(current_task)
        print(mihwar_result["response"])

        print("\n[2/2] Bayyinah reviewing...")
        bayyinah_result = _call_bayyinah_code(
            mihwar_result["response"],
            context=f"Review Mihwar output for task: {task} (cycle {cycle})",
        )

        print(f"\nVERDICT: {bayyinah_result['verdict']}")
        print(bayyinah_result["report"])

        if bayyinah_result["verdict"] == "APPROVE":
            print(f"\n✓ Approved by Bayyinah on cycle {cycle}.")
            break

        if cycle == max_cycles:
            print(f"\n⚠ Max revision cycles ({max_cycles}) reached.")
            print("Escalating to human review. Do not merge without approval.")
            sys.exit(2)

        current_task = (
            f"Original task: {task}\n\n"
            f"Bayyinah review findings (cycle {cycle}):\n"
            f"{bayyinah_result['report']}\n\n"
            f"Fix all CRITICAL and HIGH findings and regenerate the full implementation."
        )
        print(f"\nRevising based on Bayyinah feedback...")


# ── Info command ───────────────────────────────────────────────────────────

def show_info() -> None:
    config = load_config()
    agents = config.get("agents", {})

    print("\n── CurLexAI Coding Agents ──────────────────────────────")
    for name, agent in agents.items():
        model = agent.get("model", {})
        modal_cfg = agent.get("modal", {})
        print(f"\n  {agent['display_name']}")
        print(f"  Tier:    {agent['tier']}")
        print(f"  Model:   {model.get('id', '?')}")
        print(f"  Size:    {model.get('size', '?')}")
        print(f"  Context: {model.get('context_window', '?')} tokens")
        print(f"  GPU:     {modal_cfg.get('gpu', '?')} x{modal_cfg.get('gpu_count', 1)}")
        print(f"  Tasks:")
        for t in agent.get("tasks", []):
            print(f"    - {t}")
    print()


# ── Utilities ──────────────────────────────────────────────────────────────

def _check_modal() -> None:
    result = subprocess.run(["modal", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        _die("Modal CLI not found. Run: pip install modal && modal token set ...")


def _die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


# ── CLI entrypoint ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CurLexAI Agent Invoker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # mihwar
    p_mihwar = subparsers.add_parser("mihwar", help="Call Mihwar (code generation)")
    p_mihwar.add_argument("task", help="Task description")

    # bayyinah
    p_bayyinah = subparsers.add_parser("bayyinah", help="Call Bayyinah (code review)")
    group = p_bayyinah.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", metavar="PATH", help="Review a file")
    group.add_argument("--diff", action="store_true", help="Review current git diff")
    group.add_argument("--code", metavar="TEXT", help="Review a code snippet")

    # pipeline
    p_pipeline = subparsers.add_parser("pipeline", help="Mihwar generates + Bayyinah reviews")
    p_pipeline.add_argument("task", help="Task description")

    # info
    subparsers.add_parser("info", help="Show agent configuration")

    args = parser.parse_args()

    if args.command == "mihwar":
        result = call_mihwar(args.task)
        print(result["response"])

    elif args.command == "bayyinah":
        if args.file:
            result = call_bayyinah_file(args.file)
        elif args.diff:
            result = call_bayyinah_diff()
        else:
            result = _call_bayyinah_code(args.code)
        print(f"VERDICT: {result['verdict']}")
        print(result["report"])

    elif args.command == "pipeline":
        run_pipeline(args.task)

    elif args.command == "info":
        show_info()


if __name__ == "__main__":
    main()
