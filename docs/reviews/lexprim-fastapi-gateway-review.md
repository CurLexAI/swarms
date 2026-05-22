# Review — Proposed LexPrim FastAPI Gateway (`main.py`)

- **Reviewer:** Repository operator
- **Review date:** 2026-05-22
- **Branch:** `claude/lexprim-fastapi-gateway-review-4xtzH`
- **Subject:** External proposal to introduce a FastAPI gateway
  (`main.py`) bundling Ollama, Cursor Cloud, Llama 4 on Vertex AI, and
  a generic "automation" surface, and to position it as the program's
  primary server.
- **Outcome:** **HOLD.** Reject as primary runtime. Permit only as
  a secondary adapter behind the existing Node/Express runtime — see
  `docs/decisions/ADR-0006-fastapi-secondary-ai-gateway.md`.
- **Status (per Execution Discipline Maximum):**
  `CHANGED_BUT_NOT_VERIFIED` — verdict recorded; no code merged in this PR.

## Executive verdict

Do **not** merge the proposed FastAPI bundle as the primary server for
LexPrim / Qarar. The current shape is acceptable only as a *prototype
gateway*. The merge decision is **HOLD** until either:

1. The proposal is restructured as a subordinate layer behind the
   existing Node/Express runtime, satisfying every constraint in
   ADR-0006; or
2. An explicit superseding ADR is approved that makes FastAPI the new
   operational runtime — addressing migration of the Node runtime's
   startup gates, ADR-0001's forbidden-paths list, and ADR-0005's
   public-gateway decision.

## What the proposal contains

A single-file FastAPI application that exposes:

- `/v1/agent` — direct dispatch to one of: a local Ollama agent, a
  Cursor Cloud agent (subprocess `cursor-agent --api-key …`), a
  Llama 4 agent on Google Vertex AI.
- `/v1/automation` — named workflows
  (`triage_linear`, `investigate_sentry`, `investigate_datadog`,
  `product_faq`) implemented as prompt wrappers, with no actual
  integration to Linear / Sentry / Datadog / Notion.
- A coordinator that picks a provider based on `agent_type` and prompt
  length.
- Hand-rolled settings (not `pydantic-settings`).

No such `main.py` is present in this repository — verified on
2026-05-22 via `find . -name main.py -not -path "*/node_modules/*"
-not -path "*/.git/*"` (returns empty). This review is therefore a
gate on **inbound** code, not on an existing merge.

## Verified evidence (against the current repository)

The following observations are `VERIFIED` against the working tree on
branch `claude/lexprim-fastapi-gateway-review-4xtzH` on 2026-05-22:

1. **Operational runtime source of truth is Node.**
   - `docs/operations/canonical-runtime-paths.md` declares TypeScript
     under `src/**/*.ts` with build output under `dist/`.
   - `scripts/check-service-divergence.mjs` enforces TS/JS pair
     consistency.
   - `package.json` is `"type": "module"`, `node >=20.0.0`.
   - A Python FastAPI process is not part of this chain.

2. **Control plane is registry-driven.**
   - `.agents/config/agents.yaml` is canonical (per `CLAUDE.md`).
   - `agents/registry.yaml` is the legacy fallback.
   - `.agents/validate.py` validates registry integrity.
   - `unifiedAgentAdapter` (`src/services/unifiedAgentAdapter.ts/.js`)
     reads from this registry. A Python factory in `main.py` would
     bypass it entirely.

3. **Public-LLM-gateway question is closed for now.**
   - `docs/decisions/ADR-0005-public-llm-gateway.md` selects Option A
     (Reject); sovereign posture preserved.
   - Existing scaffolding at `.agents/gateway/` returns HTTP 501 by
     design and refuses to start without
     `SWARMS_GATEWAY_STUB_ACK=1`.

4. **ADR-0001 forbids paths the proposal would naturally claim.**
   - Forbidden additions include `backend_fastapi/`, `src/api/`,
     `src/routes/`, public REST/GraphQL surfaces, `autoStart` flags.
   - `scripts/commander/adr-0001-boundary-gate.sh` enforces this list
     mechanically.

5. **No `main.py` in the working tree** — verified via `find` on
   2026-05-22.

## Inferred / unverified context

- **Node runtime security envelope** (domain redirect, CORS/CSP,
  Helmet, raw webhook body, Iron Dome, honeytoken, LAN/mobile
  controls, prompt-injection shield, rate limits,
  `protectedApiGate`) — `INFERRED` from operator description. Not
  re-validated against `src/app.js` in this review pass. ADR-0006
  treats it as a present-tense fact for decision purposes; a
  follow-up audit may downgrade individual items.

## Risk register

Findings are labeled by the conventions in `CLAUDE.md`
("EXECUTION DISCIPLINE MAXIMUM").

### CRITICAL — `/v1/agent` and `/v1/automation` have no authentication

Any caller reachable on the listener (especially if bound to
`0.0.0.0`) can invoke local or cloud agents, submit arbitrary
prompts, run workflows, and potentially consume Cursor / Vertex AI
credits at the operator's expense. Unacceptable even on a developer
laptop.

**Required fix:** mirror Node's `protectedApiGate` in FastAPI:
API key or JWT, RBAC, request-id correlation, rate limit, audit log.
Sensitive endpoints default-off; explicit opt-in per environment.

### CRITICAL — `image_path` enables local file disclosure

`DirectAgentRequest.image_path` accepts a filesystem path as a string;
`llama4_agent.py` opens the file directly and forwards it to the
model. If an unauthenticated attacker (see above) can reach the
endpoint, they can read arbitrary local files reachable by the
process UID.

**Required fix:** do not accept paths from the user. Accept uploads
only — size-bounded, MIME and magic-byte validated, written to a
restricted temp path, deleted after processing.

### HIGH — sovereign-data violation via size-based routing

The coordinator routes "long" code prompts to Cursor Cloud or
Vertex AI Llama 4. Routing on prompt size is not a residency policy.
In Qarar's sovereign-data context, this could send `CONFIDENTIAL` /
`RESTRICTED` content to a non-sovereign provider in a non-approved
region.

**Required fix:** make `data_classification`
(`PUBLIC` | `INTERNAL` | `CONFIDENTIAL` | `RESTRICTED`) a mandatory
input. Refuse to dispatch `CONFIDENTIAL` / `RESTRICTED` to any
non-sovereign provider in code, not in documentation.

### HIGH — registry/governance bypass

Python agent factories declared in `main.py` create a third
"source of truth" beside `.agents/config/agents.yaml` and
`agents/registry.yaml`. Validators (`.agents/validate.py`,
`agent-presence-gate.sh`, `unifiedAgentAdapter`'s schema checks)
become non-authoritative the moment a Python factory diverges from
the registry.

**Required fix:** the FastAPI adapter reads agents from
`.agents/config/agents.yaml` (with the legacy fallback) and never
defines agents inline.

### HIGH — Cursor API key passed in `argv`

`CursorCloudAgent.run()` shells out to `cursor-agent --api-key <KEY>`.
Process listings (`ps`, `/proc/*/cmdline`, container logs, eBPF
exporters) capture full `argv`. Secrets in `argv` are a known leak
class.

**Required fix:** pass secrets via environment variable, stdin, or a
secret store. Never in `argv`. Audit logs must scrub command lines
even when they look secret-free.

### HIGH — "automation" endpoints without integrations

`triage_linear`, `investigate_sentry`, `investigate_datadog`,
`product_faq` are prompt-wrappers — no Linear / Sentry / Datadog /
Notion client is wired. Naming them after the systems they pretend to
integrate with creates a false sense of operational coverage and
trains downstream consumers (humans, scripts, ops dashboards) on a
lie.

**Required fix:** rename to `draft_*` until an integration exists, or
implement the integration. Names that imply integrations they do not
have are forbidden by ADR-0006 constraint #11.

### MEDIUM — blocking I/O inside async endpoints

`agent.run()`, `requests.get()`, and `subprocess.run()` are
synchronous. Inside FastAPI `async def` handlers they block the event
loop and serialize concurrent requests.

**Required fix:** `fastapi.concurrency.run_in_threadpool` for sync
clients, or switch to async clients (`httpx.AsyncClient`,
`asyncio.create_subprocess_exec`). Queue long-running jobs.

### MEDIUM — hand-rolled, unvalidated settings

`Settings` is hand-rolled; no startup validation. Combinations like
`LLAMA4_ENABLED=true` with `GOOGLE_PROJECT_ID=None` fail late, at
first request. Invalid `LOG_LEVEL` may break startup non-obviously.

**Required fix:** `pydantic-settings` with `SecretStr`, enum log
levels, and cross-field validators that ensure each enabled provider
has the secrets it needs **before** the listener starts.

## Architectural recommendation

The defensible position for FastAPI in this repository is **secondary
AI execution adapter**, owned by Mihwar, behind the Node runtime —
not the operational entrypoint. The intended topology is:

```
Node / Express Runtime (src/server.js -> src/app.js)
  -> protectedApiGate
  -> /api/orchestrator (Node)
    -> FastAPI AI Gateway (loopback / internal only)
      -> Policy gate (auth + RBAC)
      -> Data-classification gate
      -> Sovereign router (reads .agents/config/agents.yaml)
      -> Ollama (local) / Modal (Mihwar, Bayyinah)
      -> Optional cloud (Cursor / Vertex) — PUBLIC / INTERNAL only
      -> Append-only AuditTrail (AuditService)
```

This shape is now encoded as the decision in
`docs/decisions/ADR-0006-fastapi-secondary-ai-gateway.md`. The twelve
mandatory constraints in that ADR translate the seven risks above
into binding requirements on any future PR.

## Next valid action

A single concrete next step is authorized:

> Open a follow-up PR titled `feat(gateway): fastapi secondary
> adapter` that implements, in this order, only the first three
> capabilities: (1) authentication, (2) `data_classification` gate,
> (3) append-only audit log. **No** Cursor Cloud, Vertex AI, or
> "automation" endpoints in that PR. Cloud-provider integrations
> follow in subsequent PRs only after the three gates above are unit
> tested and proven to refuse the negative cases.

## Execution Verdict

```text
Execution Verdict:
- Status: CHANGED_BUT_NOT_VERIFIED
- Scope: Record the operator verdict on an inbound FastAPI gateway
  proposal; lock its permitted role via ADR-0006.
- Canonical Path: docs/decisions/ADR-0006-fastapi-secondary-ai-gateway.md
  and docs/reviews/lexprim-fastapi-gateway-review.md.
- Files Touched:
  - docs/decisions/ADR-0006-fastapi-secondary-ai-gateway.md (new)
  - docs/reviews/lexprim-fastapi-gateway-review.md (new)
- Blockers: none for this documentation change.
- Hot Surface Risk: Low (no code committed; documents a decision
  that *prevents* a hot-surface expansion).
- What Was Actually Changed: two new Markdown documents recording
  the verdict and the binding constraints for any future FastAPI
  adapter PR.
- What Was Actually Verified:
  - No `main.py` exists in the working tree (find).
  - ADR-0005 status is Decided — Option A.
  - The Node runtime is the canonical entrypoint per
    docs/operations/canonical-runtime-paths.md.
  - ADR-0001 forbids backend_fastapi/, src/api/, src/routes/,
    public REST/GraphQL surfaces.
- What Remains Unverified:
  - The Node runtime's security envelope (Iron Dome, honeytoken,
    prompt-injection shield, protectedApiGate) was treated as
    operator-described rather than re-audited line-by-line.
  - The downstream PR that would actually implement the secondary
    adapter has not been drafted; its constraint coverage is
    aspirational until that PR exists.
- Next Valid Action: open the follow-up PR described under
  "Next valid action" above, scoped only to auth + data
  classification + audit log.
```
