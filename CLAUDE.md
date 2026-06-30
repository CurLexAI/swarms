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
python3 -m pytest -q tests/          # or: npm run test:python
python3 -m pytest -q tests/test_router_policy.py            # single file
python3 -m pytest -q tests/test_router_policy.py::TestName  # single test

# Node tests. `npm test` is the unified-adapter suite (unit + 2 integration);
# `npm run test:node` runs every Node test (all .test.js and .test.ts via tsx).
npm test                 # unifiedAgentAdapter unit + integration
npm run test:unit        # unifiedAgentAdapter unit only
npm run test:security    # sovereignCyberRadar
npm run test:node        # all Node tests (.js then .ts)
node --test tests/unifiedAgentAdapter.test.js               # single file
node --import tsx --test tests/runtime-policy.test.ts       # a .ts test via tsx

# Security radar CLI (Sovereign Cyber Radar)
npm run security:radar:url      # scan a URL
npm run security:radar:text     # scan text
npm run security:radar:command  # scan a command
npm run security:radar:simulate

# TypeScript strict check (no emit) — needs `npm ci` first; see "Known TS blocker"
npx tsc --noEmit
# Build (emits .js next to .ts)
npm run build

# Misc developer utilities
npm run doctor:cli               # dev CLI environment diagnostics
npm run integrity:frontend       # regenerate frontend SRI/integrity manifest
npm run deploy:evidence:validate # validate launch-evidence docs

# Aggregate gate (npm run check), in order:
#   service-divergence -> unit tests -> ADR-0001 boundary -> CDN SRI ->
#   Qala audit-integrity -> swarms-presence -> Supabase public boundary ->
#   runtime-policy check -> runtime-policy test
npm run check
```

## Repository policy gates (must pass before claiming readiness)

The full gate set lives in `scripts/commander/`. The core ones:

```bash
bash scripts/commander/p0-security-test-gate.sh .          # P0 security tests
bash scripts/commander/modal-boundary-gate.sh .            # Modal stays backend-only
bash scripts/commander/adr-0001-boundary-gate.sh .         # boundary / no forbidden paths
bash scripts/commander/agent-presence-gate.sh .            # required agent assets present
bash scripts/commander/public-surface-boundary-gate.sh .   # public/ surface boundary
bash scripts/commander/qala-audit-integrity-gate.sh .      # Qala audit hash-chain integrity
bash scripts/commander/qala-egress-residency-gate.sh .     # egress/data-residency boundary
bash scripts/commander/release-readiness-gate.sh .         # aggregate launch readiness
bash scripts/commander/master-audit-gate.sh .              # chains the core gates in one pass
bash scripts/commander/agent-activation-preflight.sh .     # preflight before any activation claim
bash scripts/commander/modal-runtime-smoke.sh .            # Modal runtime smoke (needs secrets)
bash scripts/commander/repo-rename-gate.sh .               # repo-identity / rename safety
python3 scripts/commander/swarm-presence-monitor.py --repo-root . --no-network
python3 scripts/commander/copilot-agent-profiles-gate.py
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

`modal-boundary-gate.sh` blocks `*.modal.run` URLs or Modal SDK imports from leaking into public/client surfaces. `adr-0001-boundary-gate.sh` rejects the forbidden paths above and any `autoStart` activation flag in `.agents/`, `agents/`, `src/`, `public/`, `.github/`. The Qala gates enforce the security architecture in ADR-0003 (audit hash-chain, egress residency).

## Invoking agents (requires Modal + secrets)

```bash
python3 .agents/invoke.py mihwar "Describe the task"
python3 .agents/invoke.py bayyinah --diff
python3 .agents/invoke.py bayyinah --file src/auth.py
python3 .agents/invoke.py pipeline "Add rate limiting to the API"  # mihwar -> bayyinah
modal deploy .agents/modal_app.py
```

Required runtime secrets (configure in GitHub Actions / Render / secret manager — never commit): `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, and the **per-agent bearer tokens** `MIHWAR_API_TOKEN` and `BAYYINAH_API_TOKEN` (split from the retired shared-token contract — each endpoint now isolates its own token). Optional: `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `RENDER_API_TOKEN`, `CLOUDFLARE_API_TOKEN`, `SOVEREIGN_API_KEY`. When checking presence, report only `SET`/`UNSET` — never echo values. See `docs/secrets-policy.md`.

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

Default collaboration: Mihwar generates → Bayyinah reviews → up to 3 revision cycles → human approval. Bayyinah must never approve with unresolved CRITICAL/HIGH findings. The `.agents/core_coding_swarm.py` orchestrator encodes this pipeline (`phase_1_mihwar_planning` → `phase_2_bayyinah_validation`); it is offline/mock-safe by default and refuses to run when external AI is enabled.

> **Two lenses on the same three names.** The table above is the *code-level* model-assignment view (the source of truth in `.agents/config/agents.yaml`). The newer platform doctrine in `ARCHITECTURE_DIRECTIVE.md` (Arabic) describes a *system-topology* view where **Bayyinah** is the evidence/knowledge core (single source of truth, Qdrant-backed), **Mihwar** is the control/audit plane through which every interaction must pass, and **Qarar** is the public-facing interface that never touches Bayyinah directly. Keep both lenses in mind: the directive governs platform topology and compliance (ECC-2:2024, PDPL); `agents.yaml` governs which model executes which coding task.

### Key components

- **`.agents/config/agents.yaml`** — canonical agent profiles (model id, Modal endpoint, system prompts, tasks). This is the single source of truth for `unifiedAgentAdapter`; `agents/registry.yaml` is legacy-only and used strictly as an automatic fallback when `.agents/config/agents.yaml` is absent.
- **`.agents/modal_app.py`** — Modal deployment surface (vLLM endpoints `MihwarAgent`, `BayyinahAgent`).
- **`.agents/invoke.py`** — CLI to call agents. Has a fallback YAML parser so `info` works without PyYAML installed.
- **`.agents/pr_review.py`** + **`.github/workflows/agent-review.yml`** — Bayyinah review of PR diffs on `main`. Workflow runs boundary gates *before* reading secrets.
- **`.agents/router/`** — Qarar model router: `task_classifier.py` → `model_policy_engine.py` → `model_router.py` produces an `ExecutionPlan` (primary agent, validation steps, reviewer routing). Inserts `bayyinah_validation_gate` for high/critical risk tasks. `audited_router.py` wraps routing decisions with Qala trace/audit.
- **`.agents/validators/`** — programmatic gates. `bayyinah_validation_gate.py` (P0-tested in `tests/test_bayyinah_validation_gate.py`) plus the **Qala security layer** (`qala_input_gate.py`, `qala_ksa_pii.py`, `qala_trace.py`, `qala_audit_sink.py`) and `classification_validator.py` / `sovereign_security_controls.py`. Qala (قلعة, "Qal'a") is the dependency-free security architecture from `docs/decisions/ADR-0003-qala-security-architecture.md` — input validation, KSA PII redaction, trace correlation, and a sealed hash-chained audit sink. Raw secrets/PII must never enter these modules.
- **`.agents/providers/`** — provider abstractions: `modal_provider.py`, `openai_provider.py`, `anthropic_provider.py`, and local sovereign runtimes `local_ollama.py` / `local_llama_cpp.py`.
- **`.agents/mcp/`** — MCP server config and the **Aegis gateway** (`aegis_gateway.py`): a local-only, dependency-free MCP boundary that does role-based `tools/list` filtering, prompt-injection inspection of `tools/call` args, and sanitized hash-chained audit through Qala. Also hosts the Qarar API server (`qarar_api_server.py`) and Copilot/Render/Cloudflare/Modal MCP integration config.
- **`.agents/gateway/`** — **scaffolding only** for ADR-0005 (public OpenAI-compatible LLM gateway). `mcp_server.py` exposes the OpenAI *shape* but every routing endpoint returns HTTP 501 ("ADR-0005 not approved"); it calls no Modal endpoint and embeds no URL/token. The `Dockerfile` builds `swarms-gateway-stub` (deliberately not a production image name). Do not wire it to Modal until ADR-0005 is approved.
- **`.agents/core_coding_swarm.py`** — Mihwar→Bayyinah pipeline orchestrator (ADR-0001 category 1); offline/mock-safe, external-AI-denied by default. `.agents/drive_service_agent.py` and `.agents/runtime_security.py` are supporting agent-operations modules; `.agents/adapters/lexprim_bridge.py` is the (test-covered) bridge toward the LexPrim side, kept on the operations side of the boundary.
- **`.agents/catalog/agents.yaml`** — agent *catalog* (id, category, permissions, allowed/forbidden actions) for governance, distinct from the runtime profiles in `.agents/config/agents.yaml`. **`.agents/registries/`** holds the cross-client skills registry (`ai-skills.registry.yaml`, single source of truth for gemini/codex/claude-code/chatgpt skills with `no_autostart`/`no_secrets`/`no_modal_public_urls` rules) and `recovery-supervisor.yaml`. `.agents/plugins/marketplace.json` is the plugin marketplace manifest.
- **`src/services/unifiedAgentAdapter.ts`** — Node-side adapter. Loads `.agents/config/agents.yaml` (falls back to `agents/registry.yaml`), validates payloads, authorizes via `PolicyService`, and dispatches to Python or Node runtimes (dynamic import of `../runners/agentRunner.js`). Hand-maintained `.js` companion is tracked; `ControlPlaneSecurityService.js` is gitignored as tsc-emitted output.
- **`src/security/`** — TS mirrors of the Qala Python layer (`qalaTrace.ts`, `qalaKsaPii.ts`, `qalaAuditSink.ts`, `bayyinahRedactor.ts`, `contentSecurityPolicy.ts`) plus `sovereignCyberRadar.ts` — the security scanner CLI (`npm run security:radar:*`).
- **`src/runtimePolicy.ts`** / **`src/policy/runtime-policy.ts`** — runtime policy enforced by `scripts/check-runtime-policy.ts` and `tests/runtime-policy.test.ts` (both run inside `npm run check`).
- **`src/services/AuditService.ts`** + **`src/utils/auditLogger`** — audit trail used by the adapter.
- **`scripts/commander/*.sh` and `*.py`** — boundary/policy/security gates; the codex-commander skill chains them.
- **`scripts/check-service-divergence.mjs`** — verifies `.ts`/`.js` companions don't drift (run via `npm run check`). Other `npm run check` steps live in `scripts/check-*.mjs` / `check-*.ts`.

### Skills and policies (operating doctrine)

`.agents/skills/` are *playbooks* for task classes (e.g. `codex-commander`, `modal-runtime-operator`, `secure-pr-review`, `public-surface-auditor`, `agent-runtime-auditor`, `hf-cli`). `.agents/policies/` are *boundaries*; they are mandatory, not optional (`secrets-boundary.md`, `network-boundary.md`, `dependency-build-safety.md`, `qala-egress-residency.md`, `execution-discipline-maximum.md`). The Codex Commander skill (`.agents/skills/codex-commander/SKILL.md`) is the lead operating doctrine — its `references/repo-command-sequences.md`, `references/pr-playbooks.md`, and `references/commander-report-template.md` define the canonical command sequences and report format.

### Other surface directories (peripheral; respect ADR-0001 before editing)

Beyond the four allowed categories, the repo also carries operator-adjacent surfaces that are sanctioned exceptions or POCs — confirm scope against ADR-0001 before touching them:

- `mihwar-core/` — Go service skeleton for the Mihwar runtime; `windows-agent/` (C#) and `ios-companion/` (Swift) — companion clients.
- `sama_ingestion_swarm/` — SAMA document ingestion swarm (fetcher/parser/auditor/orchestrator); an ADR-0001-sanctioned POC with deps gated in `requirements-agent.txt`.
- `sovereign-connectivity-poc/`, `qarar-swarms-sovereign-integration/`, `dev-factory/`, `sovereign_network_agent_systemd_v1/` — connectivity/integration POCs and operator tooling.
- `modal/`, `mcp/`, `config/`, `agents/` (legacy `registry.yaml`) — runtime manifests and the legacy agent registry fallback.
- `artifacts/security/qala-audit.jsonl` — sealed, hash-chained Qala audit sink output (checked by `qala-audit-integrity-gate.sh`; do not hand-edit). `ci/policy-gate.yml` — PR gate reminding that registry/policy changes require an ADR + sandbox tests + Mihwar approval.

## Required conventions

- **Evidence labels.** Every material claim uses exactly one of `VERIFIED` (command output / file content / smoke test), `INFERRED` (derived but not directly proven), or `UNVERIFIED` (not checked / blocked). Use `SKIPPED_UNVERIFIED` for checks blocked by missing secrets, and `NOT_APPLICABLE` when a file/dependency is absent. Never collapse skipped into pass; never claim runtime activation without a smoke test.
- **Reports.** End substantive runs with the `COMMANDER REPORT` block from `.agents/skills/codex-commander/references/commander-report-template.md` (or the shorter form in `.agents/templates/report-template.md`).
- **Small PRs.** Split broad work into reviewable PRs with files/acceptance criteria/rollback path. Do not merge with unresolved CRITICAL or HIGH findings.
- **TS/JS companions.** Several files exist as both `.ts` and `.js` (`unifiedAgentAdapter`, `AuditService`, `sovereignCyberRadar`, `auditLogger`, `logger`, and the Qala mirrors `qalaTrace` / `qalaKsaPii` / `qalaAuditSink`). The `.js` files are hand-maintained and tracked; keep them in sync (the `check:service-divergence` step catches drift). `ControlPlaneSecurityService.js` and `src/services/unifiedAgentAdapter.*.mjs` are gitignored.
- **Known TS blocker.** `npx tsc --noEmit` requires `npm ci` first (without `node_modules` it fails early on `TS2688: Cannot find type definition file for 'node'`). Even with deps installed, type-checking is a tracked blocker: `src/runners/` ships only `agentRunner.d.ts` (no `.ts`/`.js` source), so the dynamic `import("../runners/agentRunner.js")` in `unifiedAgentAdapter.ts` has no resolvable module. Do not fabricate fixes that mask it.
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

- `AGENTS.md` — agent handbook (read first for operating model, execution order, and the Repository Activation Checklist).
- `ARCHITECTURE_DIRECTIVE.md` — platform architectural doctrine (Arabic): Bayyinah core / Mihwar control plane / Qarar public interface, the swarms-and-agents inventory, and KSA compliance controls (ECC-2:2024, PDPL). Read alongside the `agents.yaml` model-assignment view.
- `AGENT_BOOTSTRAP.md` / `ONBOARDING_CHECKLIST.md` — short bootstrap prompt and onboarding steps for a new operational agent (register identity via Mihwar, short-lived creds, read-only sandbox test, enable logging before any write).
- `INSTRUCTION_LOADING_ORDER.md` — deterministic instruction-loading policy (kernel + policies + one task mode).
- `CONSTITUTION.md` — founding charter (Arabic); founder/client rights and duties.
- `README.md` — operating-model summary and verification command list.
- `docs/decisions/` — Architecture Decision Records. Key ones:
  - `ADR-0001-swarms-boundary.md` — repository boundary (authoritative).
  - `ADR-0002-*` — repo identity, Mihwar control plane, and operator static-artifacts boundary (three records share the ADR-0002 number).
  - `ADR-0003-qala-security-architecture.md` — Qala (قلعة) security layer.
  - `ADR-0004-qala-modal-edge-hmac-auth.md` (Modal/edge HMAC auth) and `ADR-0004-canonical-platform-surfaces.md` (canonical platform surfaces).
  - `ADR-0005-public-llm-gateway.md`, `ADR-0006-fastapi-secondary-ai-gateway.md`, `ADR-0007-sovereign-incident-decision-service.md`.
- `docs/secrets-policy.md` — required/optional secrets and rotation posture.
- `docs/launch-evidence/agent-launch.md` — launch readiness template (stays pending until evidence exists).
- `docs/operations/codex-sdk-usage.md` — Codex SDK integration notes.


## GitHub Models BYOK (Organization)

Use this path when organization owners need custom model providers in GitHub Models:

1. Organization **Settings** → **Models** → **Custom models**.
2. Add API keys (currently OpenAI and AzureAI are supported in public preview).
3. Organization **Settings** → **Models** → **Development**.
4. Under model permissions choose:
   - **All publishers** to allow all API-key-backed publishers, or
   - **Only select models** to maintain an explicit allow/deny list.
5. If **All publishers** is unavailable, enable model usage policy first in organization model governance settings.

Operational safeguards:
- Apply least privilege to API keys.
- Keep billing/usage monitoring in provider dashboards.
- Never store raw keys in repo files, issues, PR comments, or logs.

## EXECUTION DISCIPLINE MAXIMUM (Claude workflow)

When operating through Claude Code in this repository, enforce these status labels only:

- `VERIFIED_FIXED`
- `PARTIALLY_APPLIED`
- `CHANGED_BUT_NOT_VERIFIED`
- `BLOCKED`
- `UNVERIFIED`
- `NOT_STARTED`
- `SUPERSEDED`
- `CONFLICTED`

Mandatory report format after each execution:

```text
Execution Verdict:
- Status:
- Scope:
- Canonical Path:
- Files Touched:
- Blockers:
- Hot Surface Risk:
- What Was Actually Changed:
- What Was Actually Verified:
- What Remains Unverified:
- Next Valid Action:
```
