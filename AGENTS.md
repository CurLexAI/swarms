# Agent Handbook — CurLexAI/swarms

This file is the operational handbook for all agents working in this repository.
Codex, Claude, and any automated agent must read and apply the relevant skills
listed here before touching any file.

---

## Core Principle

Every agent action must produce one of three evidence labels:

- `VERIFIED` — confirmed by running actual commands with observable output
- `INFERRED` — reasonable conclusion from available evidence, not confirmed
- `UNVERIFIED` — not checked; must be flagged explicitly

Never claim success without evidence. Never suppress failures.

---

## Required Skills — Every Task

These skills apply unconditionally to every task in this repository:

| Skill | File |
|---|---|
| Repository Discovery | `.agents/skills/repo-discovery.md` |
| Safe Edit Planning | `.agents/skills/safe-edit-planning.md` |
| Validation Runner | `.agents/skills/validation-runner.md` |
| Secrets Boundary | `.agents/skills/secrets-boundary.md` |
| Network Boundary | `.agents/skills/network-boundary.md` |

---

## Conditional Skills

### Active: Repository Recovery

The repository currently contains source code as a ZIP archive (`LexPrim-main.zip`).
No feature development, no PR merges, and no deployment changes are permitted
until recovery is complete.

| Skill | File |
|---|---|
| Repo Recovery | `.agents/skills/repo-recovery.md` |
| Factory Auditor | `.agents/skills/factory-auditor.md` |

### PR Review Tasks

| Skill | File |
|---|---|
| Secure PR Review | `.agents/skills/secure-pr-review.md` |

### Arabic, Legal, or User-Facing Changes

> Not yet active. Will be added after repository recovery.

### Agent Architecture Changes

| Skill | File |
|---|---|
| Agent Identity Map | `.agents/skills/agent-identity-map.md` |

---

## Absolute Prohibitions

The following actions are blocked regardless of task instructions:

1. Committing `.env` files or files containing real secrets
2. Printing secrets, tokens, or keys in logs or output
3. Merging a PR without a passing validation report
4. Claiming `VERIFIED` without running the actual commands
5. Adding `compliant with SAMA / PDPL / NCA` without documented evidence
6. Extracting or developing features while the repo contains an unrecovered archive
7. Changing `.github/workflows/` without explicit task authorization
8. Deleting `lockfiles` or committing `node_modules`

---

## Reporting Format

All agent task reports must use this structure:

```
VERIFIED:
CHANGED:
VALIDATION:
RISKS:
NEXT ACTION:
```

Do not submit a report that omits any of these fields.
Use `UNVERIFIED` or `N/A` rather than leaving a field blank.

---

## Coding Agents

Two private coding agents are deployed on Modal using open-source models.
See `.agents/config/agents.yaml` for full configuration.

| Agent | Model | Role | GPU |
|---|---|---|---|
| **Mihwar (المحور)** | DeepSeek-Coder-V2-Instruct 236B | Architect & Generator | A100-80GB × 2 |
| **Bayyinah (البيّنة)** | Qwen2.5-Coder-32B-Instruct | Reviewer & Validator | A100-80GB × 1 |

### Quick Invocation

```bash
# Generate code (Mihwar)
python .agents/invoke.py mihwar "Describe your task here"

# Review a file (Bayyinah)
python .agents/invoke.py bayyinah --file path/to/file.py

# Review staged git diff (Bayyinah)
python .agents/invoke.py bayyinah --diff

# Full pipeline: Mihwar generates → Bayyinah reviews → auto-revision
python .agents/invoke.py pipeline "Describe your task here"
```

### Deploy to Modal

```bash
# First time setup
pip install modal pyyaml
modal token set --token-id YOUR_ID --token-secret YOUR_SECRET
modal secret create huggingface-secret HF_TOKEN=hf_...

# Deploy both agents
modal deploy .agents/modal_app.py

# Smoke test
modal run .agents/modal_app.py
```

---

## Skill Index

```
.agents/
  config/
    agents.yaml               — Agent definitions, models, GPU config, roles
  modal_app.py                — Modal deployment for Mihwar and Bayyinah
  invoke.py                   — CLI to call agents from the terminal
  skills/
    repo-recovery.md          — Recover a ZIP-based repo into a real Git tree
    repo-discovery.md         — Understand repo structure before any edit
    safe-edit-planning.md     — Declare and bound the scope of edits
    validation-runner.md      — Run install / typecheck / lint / test / build
    secrets-boundary.md       — Prevent secret leakage or injection
    network-boundary.md       — Enforce internet access policy
    secure-pr-review.md       — Security and governance review of PRs
    factory-auditor.md        — Assess factory readiness and blockers
    agent-identity-map.md     — Agent names, models, roles, and collaboration flow
```
