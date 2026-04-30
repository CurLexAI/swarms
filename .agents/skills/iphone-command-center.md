# Skill: iPhone Command Center

## Purpose

Operate `CurLexAI/swarms` from an iPhone as a command center while all code execution, tests, builds, and model hosting run on a trusted workstation, VPS, GitHub runner, or Modal runtime.

The iPhone is for planning, approvals, SSH supervision, PR review, and incident response. It is not the production coding runtime.

---

## Canonical Repository

Repository: `CurLexAI/swarms`

Before running any command, confirm the remote repository and branch.

---

## Roles

| Surface | Role |
|---|---|
| ChatGPT on iPhone | Strategy, requirements, prompts, review, executive decisions |
| SSH app on iPhone | Start remote jobs, inspect logs, stop unsafe jobs |
| GitHub app/web | Review PRs and workflow status |
| Remote Linux host | Codex CLI, tests, builds, Docker, local models |
| Modal | Mihwar and Bayyinah runtime deployment |

---

## Safe Launch Sequence

Run from the remote host through SSH:

```bash
cd ~/swarms
git remote -v
git status --short
git branch --show-current
git pull --ff-only
```

Then run the repository gates that exist in this repo:

```bash
bash scripts/commander/repo-rename-gate.sh
python -m py_compile .agents/modal_app.py .agents/invoke.py .agents/pr_review.py
python .agents/invoke.py info
```

Only proceed when the repository, branch, and validation outputs are clear.

---

## Codex Operating Rules

Use Codex for bounded repository-local tasks only.

Required rules:

1. State one exact task.
2. Require machine-readable evidence when possible.
3. Use a sandboxed workspace mode.
4. Do not allow direct production deployment from a broad prompt.
5. Do not allow direct merge or force push.
6. Do not print or request secrets.
7. Require validation results or a clear blocked reason.

Safe prompt pattern:

```text
Inspect this repository, make the smallest safe repo-local change for the requested task, run available validation, and return changed files, validation output, risks, and next action. Do not merge, force push, print secrets, or deploy production.
```

---

## Local Model Routing

Local model endpoints may include Ollama, vLLM, or an internal OpenAI-compatible gateway.

Important rule: do not assume cloud agents can reach `localhost`. Any cloud worker needs a reachable remote endpoint or hosted runtime.

---

## Required Skills

| Skill | Purpose |
|---|---|
| repo-discovery | Inspect repository structure before edits. |
| safe-edit-planning | Bound file changes. |
| validation-runner | Run syntax, tests, lint, build, or report blockers. |
| secrets-boundary | Prevent token leakage. |
| network-boundary | Prevent unauthorized external calls. |
| dependency-build-safety | Control dependency and build risk. |
| secure-pr-review | Review PRs before merge. |
| factory-auditor | Assess readiness and blockers. |
| iphone-command-center | Coordinate remote work from iPhone safely. |

---

## Commander Report

Every run must end with:

```text
=== COMMANDER REPORT ===
Mission:
Priority:
Owner:
Status: PASS/FAIL/BLOCKED
Evidence:
Risks:
Decision: GO/NO-GO/needs verification
Next action:
```

---

## No-Go Conditions

- Remote does not point to `CurLexAI/swarms`.
- Direct edits are attempted on `main` without an approved workflow.
- Secrets appear in prompts, logs, comments, or files.
- Validation is skipped without an explicit reason.
- A cloud agent is expected to access a local-only endpoint.
- A broad prompt attempts production deployment without staged approval.
