# swarms

CurLexAI `swarms` is the private operator repository for Qarar/Bayyinah/Mihwar agent operations. It keeps agent profiles, skill plans, validation gates, launch-evidence templates, and operations notes for the repository control plane.

## الدستور

يخضع هذا المشروع لدستور [`CONSTITUTION.md`](CONSTITUTION.md) الذي يحدد حقوق وواجبات المؤسس والعملاء.

## Enterprise affiliation

This repository operates under the **LexPrime** GitHub Enterprise — https://github.com/enterprises/lexprime. Enterprise-level policies (SSO, audit log, IP allowlists, secret scanning, advanced security) are managed at the LexPrime org level and inherited here. Repository-level governance (ADR-0001 boundary, Codex Commander discipline, Bayyinah validation) layers on top of those enterprise controls.

## Current operating model

- **Codex Commander** is the repository execution lead skill. It scopes work, plans small PRs, runs gates, and reports with `COMMANDER REPORT` discipline.
- **Bayyinah** is the validation and review gate. Runtime activation must remain `UNVERIFIED` until endpoint smoke tests pass.
- **Mihwar** is the implementation and fix-suggestion agent. It must not be treated as live unless `MIHWAR_ENDPOINT` and `AGENT_API_TOKEN` are configured and smoke-tested.
- **Render** hosts the repository-defined `curlexai-mcp-server` Modal MCP Gateway. The BSM backend and public product API origin are distinct external services unless their source and Render blueprint are intentionally supplied to this repository.
- **Cloudflare** is the edge layer for DNS/TLS/WAF concerns.
- **Modal** is backend-only model runtime. Public browser, iPhone, or frontend code must not call `*.modal.run` directly.


## Instruction loading architecture

Instruction loading must be deterministic to prevent instruction sprawl and mode collisions.

- Canonical policy: [`INSTRUCTION_LOADING_ORDER.md`](INSTRUCTION_LOADING_ORDER.md)
- Required fixed layer: Kernel + sovereignty/connector/execution policies
- Dynamic layer: one task mode + only directly relevant domain files
- Output layer: templates only for formatting, not background reasoning

### Priority rule (conflict resolution)

Apply this precedence strictly (highest to lowest):

1. System instructions
2. Safety rules
3. Kernel
4. Policies
5. Project files
6. Mode files
7. Domain files
8. Agent profiles
9. User preference

### File header convention

Every instruction file should begin with:

- `Purpose:`
- `When to load:`

## Plans

- `docs/legal-compliance-skill-intake-plan.md` — disciplined intake plan for the `legal-compliance` skill package.
- `docs/operations/codex-sdk-usage.md` — Codex SDK integration notes for TypeScript and Python workflows.

## Key operations files

- `.agents/skills/codex-commander/SKILL.md` — Codex Commander operating doctrine.
- `.agents/skills/codex-commander/references/pr-playbooks.md` — current PR sequencing and acceptance criteria.
- `.agents/skills/codex-commander/references/repo-command-sequences.md` — repeatable repository check commands.
- `.agents/skills/codex-commander/references/commander-report-template.md` — required status-report format.
- `docs/secrets-policy.md` — required secrets and rotation posture.
- `docs/launch-evidence/agent-launch.md` — launch-readiness evidence template; keep pending until evidence exists.
- `scripts/commander/modal-boundary-gate.sh` — blocks Modal endpoint or SDK leakage into public/client surfaces and chains ADR-0001 boundary regression checks.
- `scripts/commander/adr-0001-boundary-gate.sh` — fails when forbidden application-repo surfaces drift into `swarms`.
- `scripts/commander/agent-presence-gate.sh` — checks configured agent inventory and runtime secret presence.
- `scripts/commander/p0-security-test-gate.sh` — runs P0 Bayyinah/router security policy tests.
- `scripts/commander/qala-audit-integrity-gate.sh` — verifies the Q7 sealed audit chain (`.agents/validators/qala_audit_sink.py`) is intact; fails closed on any tamper, insertion, or truncation.

## Required secrets for live runtime checks

Do not commit values. Configure these as **Organization secrets at the LexPrime enterprise org** with both `CurLexAI/swarms` and `LexPrim/Qarar` in the Selected repositories allow-list. Repository-scoped duplicates are deprecated — see `docs/secrets-policy.md §3` for the operator runbook and `§3.1` for the silent-degrade warning.

```text
BAYYINAH_ENDPOINT
MIHWAR_ENDPOINT
AGENT_API_TOKEN
```

Optional deployment/provider secrets depend on the active workflow:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
RENDER_API_TOKEN
CLOUDFLARE_API_TOKEN
SOVEREIGN_API_KEY
```


## Agent runtime validation dependencies

Use the agent-runtime dependency set only for validating agent CLI/runtime paths and tests in this repository (not as an application dependency lockfile).

```bash
pip install -r requirements-agent.txt
```

## Local verification

Run the strongest available subset from a real checkout. Each command is
expected to exit `0` unless a known blocker is recorded in `docs/decisions/`
or an open audit in `docs/audits/`.

### One-time setup

```bash
pip install -r requirements-agent.txt
npm ci
```

### Python agent gates

```bash
python3 -m py_compile .agents/*.py
python3 .agents/validate.py
python3 .agents/invoke.py info
```

### Test suites

```bash
python3 -m unittest discover -s tests
python3 -m pytest -q tests/
npm test
```

`pytest` and `unittest` cover the same Python tests; either runner is
acceptable. `npm test` runs the unified agent adapter Node test suite.

### TypeScript strict check

```bash
npx tsc --noEmit
```

### Repository policy gates

```bash
bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

`npm run check` also executes the service-divergence unit checks and the ADR-0001 boundary regression gate.

### One-command automated release gate

```bash
bash scripts/commander/release-readiness-gate.sh .
```

Exit codes:
- `0` → `READY`
- `1` → `BLOCK`
- `2` → `HOLD` (typically missing runtime secrets or non-blocking hardening gaps)

### Repository boundary

The repository scope and forbidden additions are codified in
[`docs/decisions/ADR-0001-swarms-boundary.md`](docs/decisions/ADR-0001-swarms-boundary.md).
Read it before proposing changes that add public-facing application
surfaces, RAG pipelines, frontend pages, or `autoStart` activation flags.

Secret warnings in local runs are expected unless runtime endpoints and tokens are intentionally bound. They must not be reported as verified runtime activation.

## Status language

Use the following labels consistently:

- `VERIFIED` — directly backed by command output, GitHub metadata, file content, or smoke-test evidence.
- `INFERRED` — logically derived but not directly proven.
- `UNVERIFIED` — not checked, blocked by missing secrets, blocked by runtime, or outside current access.
- `SKIPPED_UNVERIFIED` — a workflow skipped because required runtime configuration is absent.

Never claim production readiness, private Copilot `@` participants, or live Bayyinah/Mihwar operation without direct smoke-test evidence.
