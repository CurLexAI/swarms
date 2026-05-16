# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository identity

`CurLexAI/swarms` is the **agent operations and validation layer** for the CurLexAI program — not the LexPrim/Qarar application monorepo. ADR-0001 (`docs/decisions/ADR-0001-swarms-boundary.md`) is the authoritative boundary record. Read it before proposing anything that looks like product source.

Allowed content falls into four categories only:
1. Agent operations (catalog, config, providers, router, validators) under `.agents/`.
2. Modal runtime glue (`.agents/modal_app.py` and adapters in `src/services/`).
3. Validation gates (`tests/`, `scripts/commander/`, `.agents/validators/`).
4. Skills, policies, and operations docs (`.agents/skills/`, `.agents/policies/`, `docs/`).

Forbidden additions (boundary drift — gate will fail): `backend_fastapi/`, `src/routes/`, `src/pipeline/`, `src/factory/`, `src/control-hub/`, `src/api/`, `public/index.html`, marketing pages under `public/`, RAG pipelines, public REST/GraphQL surfaces, `autoStart` flags on agents, or LexPrim/Qarar product source. The `adr-0001-boundary-gate.sh` script enforces this list.

## One-time setup

```bash
pip install -r requirements-agent.txt   # pyyaml, pytest, requests, modal
npm ci
```

Node `>=20.0.0` is required. The package is ESM (`"type": "module"`).

## Common commands

```bash
# Python: validate agent assets, syntax-check, list configured agents
python3 .agents/validate.py
python3 -m py_compile .agents/*.py
python3 .agents/invoke.py info

# Tests (pytest and unittest cover the same Python tests; either works)
python3 -m unittest discover -s tests
python3 -m pytest -q tests/
python3 -m pytest -q tests/test_router_policy.py            # single file
python3 -m pytest -q tests/test_router_policy.py::TestName  # single test

# Node tests for the unified agent adapter
npm test                 # full adapter suite (3 files)
npm run test:unit        # unit only
npm run test:security    # sovereignCyberRadar
node --test tests/unifiedAgentAdapter.test.js               # single file

# TypeScript strict check (no emit)
npx tsc --noEmit
# Build (emits .js next to .ts)
npm run build

# Aggregate gate: service-divergence + unit tests + ADR-0001 boundary
npm run check
```

## Repository policy gates (must pass before claiming readiness)

```bash
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

`modal-boundary-gate.sh` blocks `*.modal.run` URLs or Modal SDK imports from leaking into public/client surfaces. `adr-0001-boundary-gate.sh` rejects the forbidden paths above and any `autoStart` activation flag in `.agents/`, `agents/`, `src/`, `public/`, `.github/`.

## Invoking agents (requires Modal + secrets)

```bash
python3 .agents/invoke.py mihwar "Describe the task"
python3 .agents/invoke.py bayyinah --diff
python3 .agents/invoke.py bayyinah --file src/auth.py
python3 .agents/invoke.py pipeline "Add rate limiting to the API"  # mihwar -> bayyinah
modal deploy .agents/modal_app.py
```

Required runtime secrets (configure in GitHub Actions / Render / secret manager — never commit): `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, `AGENT_API_TOKEN`. Optional: `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `RENDER_API_TOKEN`, `CLOUDFLARE_API_TOKEN`, `SOVEREIGN_API_KEY`. When checking presence, report only `SET`/`UNSET` — never echo values. See `docs/secrets-policy.md`.

## Architecture (big picture)

The repo describes *how* coding agents are invoked across a fixed topology:

```
User / iPhone / GitHub / Copilot
  -> Codex Commander
  -> Repository worktree
  -> Render origin
  -> Cloudflare edge
  -> Modal sovereign model runtime (Bayyinah / Mihwar via vLLM)
  -> Bayyinah validation gate
```

Three named agents and their roles are first-class concepts and appear throughout the code, configs, gates, and docs:

| Agent | Model | Role | Tier |
|---|---|---|---|
| **Mihwar** (المحور) | DeepSeek-Coder-V2-Instruct | Architect / generator | 1 |
| **Bayyinah** (البيّنة) | Qwen2.5-Coder-32B-Instruct | Reviewer / validator | 2 |
| **Copilot SWE** | GitHub Copilot | Scaffold-only executor | 3 |

Default collaboration: Mihwar generates → Bayyinah reviews → up to 3 revision cycles → human approval. Bayyinah must never approve with unresolved CRITICAL/HIGH findings.

### Key components

- **`.agents/config/agents.yaml`** — canonical agent profiles (model id, Modal endpoint, system prompts, tasks). This is the single source of truth for `unifiedAgentAdapter`; `agents/registry.yaml` is legacy-only and used strictly as an automatic fallback when `.agents/config/agents.yaml` is absent.
- **`.agents/modal_app.py`** — Modal deployment surface (vLLM endpoints `MihwarAgent`, `BayyinahAgent`).
- **`.agents/invoke.py`** — CLI to call agents. Has a fallback YAML parser so `info` works without PyYAML installed.
- **`.agents/pr_review.py`** + **`.github/workflows/agent-review.yml`** — Bayyinah review of PR diffs on `main`. Workflow runs boundary gates *before* reading secrets.
- **`.agents/router/`** — Qarar model router: `task_classifier.py` → `model_policy_engine.py` → `model_router.py` produces an `ExecutionPlan` (primary agent, validation steps, reviewer routing). Inserts `bayyinah_validation_gate` for high/critical risk tasks.
- **`.agents/validators/bayyinah_validation_gate.py`** — programmatic validation gate (P0-tested in `tests/test_bayyinah_validation_gate.py`).
- **`.agents/providers/`** — provider abstractions (`modal_provider.py`, `openai_provider.py`, `anthropic_provider.py`).
- **`.agents/mcp/`** — MCP server config for Copilot integration.
- **`src/services/unifiedAgentAdapter.ts`** — Node-side adapter that loads `agents/registry.yaml`, validates payloads, authorizes via `PolicyService`, and dispatches to Python or Node runtimes. Hand-maintained `.js` companion is tracked; `ControlPlaneSecurityService.js` is gitignored as tsc-emitted output.
- **`src/services/AuditService.ts`** + **`src/utils/auditLogger`** — audit trail used by the adapter.
- **`src/security/sovereignCyberRadar.ts`** — security scanner CLI (`npm run security:radar:*`).
- **`scripts/commander/*.sh`** — boundary/policy/security gates; the codex-commander skill chains them.
- **`scripts/check-service-divergence.mjs`** — verifies `.ts`/`.js` companions don't drift (run via `npm run check`).

### Skills and policies (operating doctrine)

`.agents/skills/` are *playbooks* for task classes. `.agents/policies/` are *boundaries*; they are mandatory, not optional. The Codex Commander skill (`.agents/skills/codex-commander/SKILL.md`) is the lead operating doctrine — its `references/repo-command-sequences.md`, `references/pr-playbooks.md`, and `references/commander-report-template.md` define the canonical command sequences and report format.

## Required conventions

- **Evidence labels.** Every material claim uses exactly one of `VERIFIED` (command output / file content / smoke test), `INFERRED` (derived but not directly proven), or `UNVERIFIED` (not checked / blocked). Use `SKIPPED_UNVERIFIED` for checks blocked by missing secrets, and `NOT_APPLICABLE` when a file/dependency is absent. Never collapse skipped into pass; never claim runtime activation without a smoke test.
- **Reports.** End substantive runs with the `COMMANDER REPORT` block from `.agents/skills/codex-commander/references/commander-report-template.md` (or the shorter form in `.agents/templates/report-template.md`).
- **Small PRs.** Split broad work into reviewable PRs with files/acceptance criteria/rollback path. Do not merge with unresolved CRITICAL or HIGH findings.
- **TS/JS companions.** Several files exist as both `.ts` and `.js` (`unifiedAgentAdapter`, `AuditService`, `sovereignCyberRadar`, `auditLogger`, `logger`). The `.js` files are hand-maintained and tracked; keep them in sync (the service-divergence check catches drift). `ControlPlaneSecurityService.js` and `src/services/unifiedAgentAdapter.*.mjs` are gitignored.
- **Known TS blocker.** `npx tsc --noEmit` currently fails with `TS2307: Cannot find module '../runners/agentRunner.js'` in `src/services/unifiedAgentAdapter.ts`. Tracked separately; do not fabricate fixes that mask it.
- **Work intake.** This repo does not use inline `TODO`/`FIXME`/`XXX`/`HACK` markers — a grep returns no real matches by design. Don't invent one. Pull next work from (in order): open issues, failing PR checks, the Activation Checklist in `AGENTS.md`, the first failing test, then documented blockers in `docs/`.

## Absolute prohibitions

1. Do not commit `.env` files, real credentials, secrets, tokens, private endpoint URLs, SSH keys, or GitHub tokens (printing them counts).
2. Do not expose `*.modal.run` endpoints to browser, iPhone, or any public/client surface — Modal is backend-only.
3. Do not claim SAMA, PDPL, NCA, or other regulatory compliance without cited evidence.
4. Do not call external AI APIs during repository work unless explicitly authorized.
5. Do not run install scripts or dependency lifecycle scripts without dependency safety review.
6. Do not commit `node_modules`, build output, caches, or opaque generated bundles as source.
7. Do not merge a PR with unresolved CRITICAL or HIGH findings.
8. Do not merge, force-push, deploy production, rotate secrets, or modify billing without explicit user approval.
9. Do not treat broad instructions ("execute everything", "نفذ كل شيء") as license to delete governance files, bypass policy, or merge unvalidated changes.

## Pointers

- `AGENTS.md` — agent handbook (read first for operating model and execution order).
- `README.md` — operating-model summary and verification command list.
- `docs/decisions/ADR-0001-swarms-boundary.md` — repository boundary (authoritative).
- `docs/secrets-policy.md` — required/optional secrets and rotation posture.
- `docs/launch-evidence/agent-launch.md` — launch readiness template (stays pending until evidence exists).
- `docs/operations/codex-sdk-usage.md` — Codex SDK integration notes.
