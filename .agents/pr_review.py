"""
CurLexAI PR Review Orchestrator
=================================
Called by GitHub Actions on every pull request.
Sends the diff to Bayyinah (review) or Mihwar (fix suggestions),
then posts a formatted comment on the PR.

Usage (from GitHub Actions):
    python .agents/pr_review.py \\
        --diff /tmp/pr.diff \\
        --pr 7 \\
        --repo CurLexAI/swarms \\
        --head-sha abc123 \\
        --agent bayyinah

    python .agents/pr_review.py \\
        --diff /tmp/pr.diff \\
        --pr 7 \\
        --repo CurLexAI/swarms \\
        --head-sha abc123 \\
        --agent mihwar \\
        --bayyinah-report "VERDICT: REQUEST_CHANGES ..."

Required environment variables:
    GITHUB_TOKEN        — provided automatically by GitHub Actions
    AGENT_API_TOKEN     — shared secret for Modal endpoint auth
    BAYYINAH_ENDPOINT   — deployed Modal web URL for Bayyinah
    MIHWAR_ENDPOINT     — deployed Modal web URL for Mihwar (optional)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path

import requests

GITHUB_API = "https://api.github.com"
MAX_DIFF_CHARS = 60_000   # Bayyinah context limit safety margin
MAX_COMMENT_CHARS = 65_000  # GitHub comment limit


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    diff = _load_diff(args.diff)

    if not diff.strip():
        print("Empty diff — skipping review.")
        sys.exit(0)

    if args.agent == "bayyinah":
        _run_bayyinah(diff, args)
    elif args.agent == "mihwar":
        _run_mihwar(diff, args)
    else:
        print(f"Unknown agent: {args.agent}", file=sys.stderr)
        sys.exit(1)


# ── Bayyinah flow ──────────────────────────────────────────────────────────

def _run_bayyinah(diff: str, args: argparse.Namespace) -> None:
    endpoint = _require_env("BAYYINAH_ENDPOINT")
    token = _require_env("AGENT_API_TOKEN")

    print(f"Calling Bayyinah at {endpoint}...")

    payload = {
        "token": token,
        "code": diff[:MAX_DIFF_CHARS],
        "context": (
            f"PR #{args.pr} in {args.repo} — reviewing git diff against main branch.\n"
            f"HEAD: {args.head_sha}"
        ),
    }

    result = _call_endpoint(endpoint, payload)

    if "error" in result:
        _post_comment(
            args,
            _error_comment(result["error"]),
        )
        sys.exit(1)

    verdict = result.get("verdict", "UNKNOWN")
    report = result.get("report", "No report returned.")
    model = result.get("model", "Qwen2.5-Coder-32B-Instruct")

    comment = _bayyinah_comment(verdict, report, model, args)
    _post_comment(args, comment)

    # Export verdict for the mihwar-fix job condition
    _set_output("verdict", verdict)
    _set_output("report", report[:4000])

    print(f"Bayyinah verdict: {verdict}")
    if verdict == "REQUEST_CHANGES":
        sys.exit(1)   # marks the check as failed → blocks merge


# ── Mihwar flow ────────────────────────────────────────────────────────────

def _run_mihwar(diff: str, args: argparse.Namespace) -> None:
    endpoint = _require_env("MIHWAR_ENDPOINT")
    token = _require_env("AGENT_API_TOKEN")
    bayyinah_report = args.bayyinah_report or os.environ.get("BAYYINAH_REPORT", "")

    print(f"Calling Mihwar at {endpoint}...")

    task = (
        f"PR #{args.pr} in {args.repo} has the following diff:\n\n"
        f"{diff[:MAX_DIFF_CHARS]}\n\n"
        f"Bayyinah (code reviewer) found these issues:\n\n"
        f"{bayyinah_report}\n\n"
        f"For each CRITICAL and HIGH finding, provide:\n"
        f"1. The exact fix as a code snippet\n"
        f"2. The file path and line number\n"
        f"3. A one-sentence explanation\n"
        f"Do not rewrite unrelated code."
    )

    payload = {
        "token": token,
        "task": task,
        "context_files": {},
    }

    result = _call_endpoint(endpoint, payload)

    if "error" in result:
        _post_comment(args, _error_comment(result["error"]))
        sys.exit(1)

    response = result.get("response", "No suggestions returned.")
    model = result.get("model", "DeepSeek-Coder-V2-Instruct")

    comment = _mihwar_comment(response, model, args)
    _post_comment(args, comment)
    print("Mihwar fix suggestions posted.")


# ── GitHub comment formatting ──────────────────────────────────────────────

def _bayyinah_comment(
    verdict: str, report: str, model: str, args: argparse.Namespace
) -> str:
    verdict_icon = "✅" if verdict == "APPROVE" else "🔴"
    verdict_label = "APPROVED" if verdict == "APPROVE" else "CHANGES REQUESTED"

    return textwrap.dedent(f"""\
        ## {verdict_icon} Bayyinah Code Review — {verdict_label}

        > **Agent:** Bayyinah (البيّنة) — Private Coding Agent
        > **Model:** `{model}`
        > **PR:** #{args.pr} · **Commit:** `{args.head_sha[:8]}`

        ---

        {_truncate(report, MAX_COMMENT_CHARS - 400)}

        ---

        <details>
        <summary>About this review</summary>

        This review was performed automatically by **Bayyinah**, a private code-review
        agent running `{model}` on Modal cloud infrastructure.
        Bayyinah reviews every PR for bugs, security issues, and correctness.

        If Bayyinah requested changes and you believe the findings are incorrect,
        tag a human reviewer for a second opinion.
        </details>
    """)


def _mihwar_comment(response: str, model: str, args: argparse.Namespace) -> str:
    return textwrap.dedent(f"""\
        ## 🔧 Mihwar Fix Suggestions

        > **Agent:** Mihwar (المحور) — Private Coding Agent
        > **Model:** `{model}`
        > **PR:** #{args.pr} · **Commit:** `{args.head_sha[:8]}`
        > **Triggered by:** Bayyinah requested changes

        ---

        {_truncate(response, MAX_COMMENT_CHARS - 400)}

        ---

        <details>
        <summary>About these suggestions</summary>

        These fix suggestions were generated automatically by **Mihwar**, a private
        code-generation agent running `{model}` on Modal cloud infrastructure.
        Mihwar produced these suggestions based on Bayyinah's review findings.

        Apply fixes at your discretion. Always verify before committing.
        </details>
    """)


def _error_comment(error: str) -> str:
    return textwrap.dedent(f"""\
        ## ⚠️ Agent Review Error

        The agent could not complete the review.

        **Error:** `{error}`

        Please check the Actions log for details, or run the review manually:
        ```bash
        python .agents/invoke.py bayyinah --diff
        ```
    """)


# ── GitHub API ─────────────────────────────────────────────────────────────

def _post_comment(args: argparse.Namespace, body: str) -> None:
    token = _require_env("GITHUB_TOKEN")
    url = f"{GITHUB_API}/repos/{args.repo}/issues/{args.pr}/comments"

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"body": body},
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        print(
            f"Failed to post comment: {resp.status_code} {resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Comment posted: {resp.json().get('html_url', '')}")


# ── Modal endpoint call ────────────────────────────────────────────────────

def _call_endpoint(url: str, payload: dict) -> dict:
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=300,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Agent timed out after 300s"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


# ── Utilities ──────────────────────────────────────────────────────────────

def _load_diff(path: str) -> str:
    p = Path(path)
    if not p.exists():
        print(f"Diff file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return p.read_text(encoding="utf-8", errors="replace")


def _require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n_[Report truncated — see Actions log for full output]_"


def _set_output(name: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"{name}={value}\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CurLexAI PR Review Orchestrator")
    parser.add_argument("--diff", required=True, help="Path to diff file")
    parser.add_argument("--pr", required=True, type=int, help="PR number")
    parser.add_argument("--repo", required=True, help="GitHub repo (owner/name)")
    parser.add_argument("--head-sha", required=True, dest="head_sha", help="HEAD commit SHA")
    parser.add_argument(
        "--agent",
        required=True,
        choices=["bayyinah", "mihwar"],
        help="Which agent to invoke",
    )
    parser.add_argument(
        "--bayyinah-report",
        dest="bayyinah_report",
        default="",
        help="Bayyinah report text (for Mihwar fix flow)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
