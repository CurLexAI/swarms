# ADR-0005 — Public OpenAI-Compatible LLM Gateway in Front of Modal (Mihwar / Bayyinah)

- **Status:** Decided — Option A (sovereign posture preserved). Revisit only when both conditions met: (a) ADR-0006 fully drafted and reviewed; (b) at least one operator user blocked by current platform.
- **Status:** Decided — Option A. Revisit only when both conditions met: (a) ADR-0006 fully drafted and reviewed; (b) at least one operator user blocked by current platform
- **Decision date:** 2026-05-22
- **Decision recorded:** 2026-05-22
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none
- **Relates to:** ADR-0001 (swarms boundary), ADR-0003 (Qal'a security architecture), ADR-0004 (Modal-Edge HMAC authentication)
- **Hot-surface classification:** YES — proposal expands the public/client surface of the sovereign model runtime

## Context

A topology proposal arrived via operator chat (2026-05-22) requesting that
Mihwar (`deepseek-ai/DeepSeek-Coder-V2-Instruct`) and Bayyinah
(`Qwen/Qwen2.5-Coder-32B-Instruct`) — currently reachable only as private
Modal web endpoints behind a bearer token (see `.agents/modal_app.py` and
ADR-0004) — be re-exposed as **OpenAI-compatible model providers** under a
single public URL, e.g. `https://agents.lexprim.com/v1/chat/completions`,
so that the following third-party client tools can address them as if they
were OpenAI:

- **Codex CLI** via `~/.codex/config.toml` `[model_providers.*]` entries.
- **Claude Code** via `--mcp` flag.
- **Cursor** via `openaiApiBase` + `openaiApiKey`.
- **Continue.dev** via `models[].apiBase`.
- **OpenWebUI** via "OpenAI Compatible API" connection.

The proposed runtime envelope from the request:

```
Codex Commander -> Mihwar Orchestrator -> Bayyinah Validator
                       -> Modal GPU Workers -> Qdrant / Retrieval
```

The proposal also asks that a gateway process (`uvicorn mcp_server:app` or
a Docker image named `lexprim-gateway`) be stood up locally on port 8080
to provide the OpenAI-compatible facade. Neither `mcp_server.py` nor that
Dockerfile currently exists in this repository.

This ADR exists because the proposal **directly conflicts** with two
standing non-negotiable boundaries, and because the right way to revisit
those boundaries is a recorded decision, not a side-channel command
sequence.

## Boundaries this proposal would cross

### 1. ADR-0001 — Repository Boundary

ADR-0001 forbids "Public REST or GraphQL API surfaces" in this repo and
constrains Modal endpoints to operator-private use. An OpenAI-compatible
HTTP surface at `agents.lexprim.com/v1`, addressable by client tools
running on developer laptops and by browser-based editors, is exactly
such a public REST surface.

### 2. `codex-commander` SKILL.md — Non-negotiable boundaries

The skill `.agents/skills/codex-commander/SKILL.md` lists, as
non-negotiable:

> Do not expose `*.modal.run` endpoints to browser, iPhone, or public
> frontend code.

The intent is "Modal is backend-only." Whether the public URL string
contains `modal.run` or is fronted by `agents.lexprim.com` is irrelevant
to the intent: any client tool (Cursor, OpenWebUI, Claude Code in a
local IDE, browser-resident model selectors) is "public frontend" for
the purposes of this rule.

### 3. CLAUDE.md absolute prohibition #2

> Do not expose `*.modal.run` endpoints to browser, iPhone, or any
> public/client surface — Modal is backend-only.

Same surface, restated as a hard prohibition.

### 4. `modal-boundary-gate.sh`

The current gate searches `src` and `public` for any `*.modal.run`
reference and fails on a hit. It does not yet model the "domain-fronted
public LLM gateway" case at all, because no such gateway exists.

## Decision (decided)

Operator decision on 2026-05-22: **Option A (Reject)** is retained.

Decision rationale:
- ADR-0006 is not fully drafted/reviewed (auth, rate-limit, billing, log retention remain incomplete).
- No operator user has been demonstrated as blocked by the current platform posture.
- Option C weakens Bayyinah's validator-of-Mihwar enforcement path.

This ADR previously proposed one of three possible outcomes; these are kept below for traceability.
The ADR records the request and the structural cost of each option so
that the decision is not made by accident:

### Option A — **Reject**

Keep the current sovereign-only posture. Mihwar and Bayyinah remain
reachable only via Modal web endpoints with the auth scheme defined in
ADR-0004. Client tools that want a Mihwar-style coding model continue to
use their own OpenAI / Anthropic providers. No code change; this ADR is
closed as "Rejected — sovereign posture preserved".

### Option B — **Accept, but constrain to operator-only ingress**

A new gateway service is stood up **outside this repository** (operator
infrastructure — not committed to `CurLexAI/swarms`). It:

- requires a Qal'a-issued HMAC-signed identity per ADR-0004,
- enforces an allowlist of caller key-ids (operator workstation, GHA
  runners, etc.) — not "the public",
- enforces per-tenant rate limits and audit logging,
- exposes an OpenAI-compatible shim **only** to those allowlisted
  callers (not to OpenWebUI, not to browser editors, not to Cursor
  installations on un-enrolled machines).

Under Option B the gateway is still "public" in the DNS sense, but it is
operationally private. The change to `swarms` would be limited to a new
policy file under `.agents/policies/` recording the constraint, and a
companion update to the codex-commander SKILL.md clarifying that
"Modal-backed gateways with Qal'a HMAC ingress are not 'public frontend'
for the purposes of this skill."

### Option C — **Accept fully — public OpenAI-compatible model provider**

The gateway is exposed to general client tools as proposed. This
requires *all* of the following before implementation:

1. **ADR-0001 amendment** — remove "Public REST or GraphQL API surfaces"
   from the forbidden list, or scope it to specifically exclude the LLM
   gateway. The amendment must list the LLM gateway as a sanctioned
   exception, not silently drop the prohibition.
2. **codex-commander SKILL.md amendment** — rewrite the "Do not expose
   Modal endpoints to public frontend code" boundary; replace it with a
   narrower rule that names the sanctioned gateway shape.
3. **CLAUDE.md amendment** — same as above for absolute prohibition #2.
4. **`modal-boundary-gate.sh` update** — teach the gate to distinguish
   sanctioned gateway hostnames from unsanctioned Modal exposure.
5. **New ADR-0006** — define the gateway's threat model, authentication
   model (whether per-user API keys, per-tool keys, or HMAC), rate limits,
   abuse handling, billing, log-retention posture, and incident-response
   ownership. None of these are defined in the current proposal.
6. **Policy file** — `.agents/policies/public-llm-gateway.md` capturing
   the operating envelope, key rotation cadence, and revocation drills.
7. **New gate** — a programmatic check that the gateway's OpenAI shim
   does not leak system prompts, validator outputs, or tool definitions
   intended for internal-only consumption.

Until **all seven** are in place, Option C cannot be implemented; a
partial implementation would create a public surface without policy
backing.

## Decision record (2026-05-22)

Operator selected **Option A — Reject; sovereign posture preserved.**
The Option B and Option C bodies above are retained for historical
context only; neither is in effect under this decision.

Rationale (verbatim from operator):

1. ADR-0006 is not yet drafted. Authentication model, rate limits,
   billing, and log-retention posture for a public gateway are all
   undefined; standing up the surface before those exist would create a
   public attack surface without policy backing.
2. No operator-tier user has been demonstrated to be blocked by the
   current Modal-private posture. The proposal solves a hypothetical
   need, not an observed one.
3. Option C would break Bayyinah's `validator-of-Mihwar` role: external
   OpenAI-compatible clients could call Mihwar directly, bypassing
   Bayyinah review and degrading the two-tier guarantee that the rest of
   the architecture is built on.

Revisit conditions (both must be met before this decision is reopened):

- ADR-0006 is fully drafted and reviewed, covering threat model,
  authentication, rate limits, billing, log retention, and
  incident-response ownership.
- At least one operator-tier user is concretely blocked by the current
  Modal-private posture, with the blocking workflow named.

The `.agents/gateway/` scaffolding stub (PR #195) is intentionally left
in place as inert exploration; it is not activated by this decision and
is not deleted, by explicit operator instruction.

## Out of scope for this ADR

- The choice between Cloudflare Worker, Render service, or self-hosted
  edge for the gateway runtime (deferred to ADR-0006 if Option B or C is
  chosen).
- The OpenAI compatibility layer itself (`mcp_server.py` /
  `lexprim-gateway` Dockerfile). Neither exists in this repo today; this
  ADR does not request that they be added until an option is chosen.
- Modal deployment of `mihwar_generate_web` / `bayyinah_review_web`. That
  is operator runtime work covered by ADR-0004 and CLAUDE.md prohibition
  #8 (production deploy requires explicit approval).
- The `~/.codex/config.toml` and per-client (Cursor / Continue.dev /
  OpenWebUI) wiring. Those are operator-machine configuration steps and
  do not belong in this repository regardless of which option is chosen.

## Consequences

### If Option A is chosen
- No code change.
- Current sovereign posture is preserved.
- Client tools that need a "Mihwar provider" must keep using OpenAI /
  Anthropic providers, OR operators run them against Modal via
  `.agents/invoke.py` from a trusted host.

### If Option B is chosen
- One new policy file in this repo; minor SKILL.md clarification.
- Gateway service lives outside this repo.
- Ingress remains operator-only; the program's sovereign posture is
  preserved at the architecture level even though DNS is public.

### If Option C is chosen
- This repo undergoes coordinated edits across ADR-0001, CLAUDE.md, the
  codex-commander skill, `modal-boundary-gate.sh`, and `.agents/policies/`.
- A new ADR-0006 captures the gateway-specific design.
- Public abuse surface, billing surface, and per-tenant trust surface all
  appear and must be operationally owned.
- Bayyinah's role as "validator-of-Mihwar" is harder to enforce when
  external tools can call Mihwar directly without routing through it.

## Verification

This ADR has been satisfied. On 2026-05-22 the operator selected
**Option A** (see "Decision record" above). Revisit requires both
conditions in the Status line — ADR-0006 drafted and reviewed, AND at
least one operator user blocked by the current platform.

ADR-0001, codex-commander SKILL.md, and CLAUDE.md prohibitions remain
authoritative under this decision.

## References

- `docs/decisions/ADR-0001-swarms-boundary.md`
- `docs/decisions/ADR-0003-qala-security-architecture.md`
- `docs/decisions/ADR-0004-qala-modal-edge-hmac-auth.md`
- `.agents/skills/codex-commander/SKILL.md` — "Non-negotiable boundaries"
- `CLAUDE.md` — "Absolute prohibitions" #2
- `scripts/commander/modal-boundary-gate.sh`
- `.agents/modal_app.py`
