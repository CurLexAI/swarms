# ADR-0006 — FastAPI as Secondary AI Execution Adapter, Not Main Runtime

- **Status:** Decided — Secondary-only. FastAPI may exist in this repository only as a Mihwar-owned secondary adapter behind the existing Node/Express runtime, never as primary runtime, never as a public surface. Promotion to primary runtime requires an explicit superseding ADR.
- **Decision date:** 2026-05-22
- **Decision recorded:** 2026-05-22
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none
- **Relates to:** ADR-0001 (swarms boundary), ADR-0003 (Qal'a security architecture), ADR-0004 (Modal-Edge HMAC authentication), ADR-0005 (public OpenAI-compatible LLM gateway — Option A retained)
- **Hot-surface classification:** YES — proposal would touch the model execution path and could create a new public/client surface if implemented carelessly.

## Context

A topology proposal arrived via operator chat (2026-05-22) describing a
FastAPI application (`main.py`) that bundles together:

- a local Ollama agent,
- a Cursor Cloud agent driven via the `cursor-agent` CLI,
- a Llama 4 agent on Google Vertex AI,
- a generic "automation" surface with named workflows
  (`triage_linear`, `investigate_sentry`, `investigate_datadog`,
  `product_faq`) implemented as prompt-wrappers,
- HTTP endpoints `/v1/agent` and `/v1/automation` without authentication,
- a routing decision based on `agent_type` and prompt length, **not** on
  data classification or residency policy.

No such `main.py` currently exists in this repository — `find` returns no
match (`VERIFIED 2026-05-22`). The proposal therefore represents an
**external/inbound** integration request, not an existing in-tree change.

This ADR exists to record the decision on whether to accept that
proposal, and on what shape, **before** any code is committed. ADR-0005
already established that the program's sovereign posture is preserved
(Option A); ADR-0006 must not silently undo that decision by introducing
a different gateway under a different name.

## The mismatch this ADR resolves

The proposed `main.py` would, if merged as a primary runtime, **collide
with at least six standing facts about this repository**:

### 1. The Node/Express runtime is the operational source of truth

Per `docs/operations/canonical-runtime-paths.md` and the
`scripts/check-service-divergence.mjs` guard, the runtime entrypoint is
`package.json` → `src/server.js` → `src/app.js`, and the canonical
TypeScript source lives under `src/**/*.ts`. A Python FastAPI process
listening on `0.0.0.0` is not part of this runtime chain and cannot be
inserted into it without an explicit ADR amendment.

### 2. The control plane is registry-driven, not factory-driven

`.agents/config/agents.yaml` is the canonical agent profile source (see
CLAUDE.md "Key components"); `agents/registry.yaml` is the legacy
fallback used only when the canonical file is absent. Python `agent
factories` defined inline in `main.py` would create a **third** source
of truth and bypass the registry/validation pipeline that
`.agents/validate.py`, `unifiedAgentAdapter`, and the boundary gates
depend on.

### 3. Sovereign routing must key on data classification, not prompt size

ADR-0003 (Qal'a security architecture) and the program's sovereign data
posture (CLAUDE.md absolute prohibition #2) require routing decisions
to consider data residency. The proposal routes "long prompts" to
Cursor Cloud or Vertex AI Llama 4 — a size-based heuristic that is
incompatible with `CONFIDENTIAL` / `RESTRICTED` handling.

### 4. The public-LLM-gateway question is already decided (ADR-0005)

ADR-0005 selected Option A (Reject) on 2026-05-22. A FastAPI app that
exposes `/v1/agent` and `/v1/automation` to a network listener is, in
substance, a new gateway. Standing one up under a different name would
re-open ADR-0005's question without re-opening the ADR.

### 5. The security envelope listed by the proposal is missing

The Node runtime's `src/app.js` carries (per repo documentation):
domain redirect, CORS/CSP, Helmet, raw webhook body, Iron Dome,
honeytoken trap, LAN/mobile controls, prompt-injection shield, rate
limits, and `protectedApiGate`. The proposed `main.py` has no
equivalent layer.

### 6. ADR-0001 forbids paths the proposal would naturally want

ADR-0001's forbidden-additions list includes `backend_fastapi/`,
`src/api/`, public REST/GraphQL surfaces, and `autoStart` activation
flags. A naive FastAPI bundle would touch at least the first three.
`adr-0001-boundary-gate.sh` would reject the PR.

## Decision

**Decided — Secondary-only.**

FastAPI is permitted to exist in this repository **only** under all of
the following constraints. Any one violation is sufficient to reject
the change.

### Mandatory constraints

1. **Role.** FastAPI is a *secondary* AI execution adapter owned by
   Mihwar. It is not the runtime entrypoint, it is not addressed by
   browser/iPhone/external clients, and it does not advertise a public
   DNS record.
2. **Path.** The adapter lives under `.agents/gateway/` (the existing
   ADR-0005 scaffolding location) or under `src/services/` as a
   subordinate of `unifiedAgentAdapter`. It does **not** live under
   `backend_fastapi/`, `src/api/`, `src/routes/`, or `public/`.
3. **Ingress.** The adapter is only reachable from the Node runtime via
   loopback or an internal network namespace; it does not bind a
   publicly routable interface. If reached at all from outside, ingress
   is mediated by the Node runtime's `protectedApiGate` (or the
   equivalent FastAPI implementation gated by the same authority).
4. **Auth.** Every adapter endpoint requires authentication. The auth
   scheme is API-key/JWT plus RBAC, mirroring the Node side; anonymous
   requests are refused, not "for development only" tolerated.
5. **Data-classification gate.** Every adapter request carries an
   explicit `data_classification`
   (`PUBLIC` | `INTERNAL` | `CONFIDENTIAL` | `RESTRICTED`). The adapter
   refuses to dispatch `CONFIDENTIAL` or `RESTRICTED` to any non-sovereign
   provider (Cursor Cloud, Vertex AI, OpenAI, Anthropic, etc.). The
   refusal is enforced in code, not in documentation.
6. **Registry adherence.** The adapter reads agent definitions from
   `.agents/config/agents.yaml` (canonical) with the legacy
   `agents/registry.yaml` fallback. It does **not** define agents
   inline in Python.
7. **Audit trail.** Every dispatch emits an append-only audit event
   compatible with `src/services/AuditService` (TS/JS pair). The audit
   record includes `agent`, `data_classification`, `provider`,
   `caller_identity`, and a hash of the prompt (not the prompt body)
   for `CONFIDENTIAL`/`RESTRICTED`.
8. **Secret handling.** Provider API keys (Cursor, Vertex, etc.) are
   read from environment / secret store and passed via env vars or
   stdin to provider clients — **never** in `argv`, **never** in shell
   command strings, **never** logged.
9. **No file-path inputs.** No endpoint accepts a local filesystem path
   as a user-controlled parameter (e.g. `image_path`). Inputs are
   accepted as uploads, size-bounded, MIME/magic-byte validated, written
   to a restricted temp path, and deleted after processing.
10. **Async discipline.** Blocking provider calls (`requests.get`,
    `subprocess.run`, synchronous SDK calls) are dispatched via
    `run_in_threadpool` or async clients. Long-running jobs use a
    queue, not in-line `await`.
11. **No "automation" without integrations.** Endpoints named after
    external systems (`triage_linear`, `investigate_sentry`,
    `investigate_datadog`, `product_faq`) are renamed `draft_*` if they
    are prompt-only, OR they carry an actual integration with the named
    system. Names that imply integrations they do not have are
    forbidden.
12. **Settings validation.** Configuration uses `pydantic-settings`
    with `SecretStr`, enums, and validators. Flags such as
    `LLAMA4_ENABLED=true` fail startup if their dependent secrets
    (`GOOGLE_PROJECT_ID`, credentials) are unset.

### Promotion to primary runtime is out of scope

This ADR does **not** authorize FastAPI to become the program's primary
runtime entrypoint. A future ADR (ADR-0007 or later) may revisit that
question; until then, `npm start` / `src/server.js` remains the only
operational entrypoint.

## Rejected alternatives

- **Accept `main.py` as proposed.** Rejected. The proposal violates
  constraints 1, 2, 3 (no auth), 4 (no auth), 5 (size-based routing),
  6 (no registry read), 7 (no audit), 8 (Cursor key in argv), 9
  (`image_path` accepted), 10 (sync in async), 11 (`triage_linear`
  without Linear), 12 (no validation).
- **Accept `main.py` as primary runtime.** Rejected. Would require
  re-opening ADR-0005, amending ADR-0001 to drop `backend_fastapi/`
  from the forbidden list, and rewriting
  `docs/operations/canonical-runtime-paths.md`. None of these
  amendments are on the table.
- **Reject FastAPI entirely.** Considered. Rejected because there is a
  defensible secondary role (Python-side adapter for Modal /
  Hugging Face / Vertex calls that the Node side cannot perform
  natively). Confining FastAPI to that role is cheaper than
  re-implementing those clients in Node.

## Consequences

### If a future PR proposes FastAPI under this ADR

It must:
- Place files under `.agents/gateway/` or `src/services/`.
- Pass `adr-0001-boundary-gate.sh`, `modal-boundary-gate.sh`,
  `agent-presence-gate.sh`, and the `codex_commander_gate.sh`.
- Include unit tests for the data-classification gate (a
  `CONFIDENTIAL` request must not reach a cloud provider).
- Include unit tests for the auth gate (anonymous request must be
  rejected with 401, not 500).
- Include an audit-trail integration test.
- Reference this ADR in the PR description.

### If a future PR proposes FastAPI as primary runtime

It must open a new ADR superseding this one, and that ADR must address:
- Migration of `src/server.js` startup gates (Iron Dome, honeytoken,
  prompt-injection shield, rate limits, `protectedApiGate`) to the new
  process.
- The TS/JS service-divergence guard's interaction with a Python
  primary.
- ADR-0001 amendment to permit a Python runtime root.
- ADR-0005 revisit (the public-gateway question changes shape under a
  Python primary).

## Verification

The decision is satisfied by this file alone. There is no code change
in this PR; subsequent PRs that add FastAPI under the secondary-only
role must reference this ADR and demonstrate compliance with the twelve
mandatory constraints above.

Evidence labels for the context section:
- "No `main.py` exists" — `VERIFIED` via `find . -name main.py` on
  2026-05-22, working tree clean on branch
  `claude/lexprim-fastapi-gateway-review-4xtzH`.
- "Node runtime is the operational source of truth" — `VERIFIED` via
  `docs/operations/canonical-runtime-paths.md` and
  `scripts/check-service-divergence.mjs`.
- "Public-LLM-gateway question is decided" — `VERIFIED` via
  `docs/decisions/ADR-0005-public-llm-gateway.md` (Status: Decided —
  Option A).
- "Security envelope of the Node runtime" — `INFERRED` from operator
  description of `src/app.js`; not re-validated in this PR.

## References

- `docs/reviews/lexprim-fastapi-gateway-review.md` — the review memo
  that drove this decision (operator verdict 2026-05-22).
- `docs/decisions/ADR-0001-swarms-boundary.md` — forbidden paths.
- `docs/decisions/ADR-0003-qala-security-architecture.md` — sovereign
  posture.
- `docs/decisions/ADR-0005-public-llm-gateway.md` — Option A retained;
  no public gateway under that ADR.
- `docs/operations/canonical-runtime-paths.md` — Node runtime is the
  source of truth.
- `.agents/gateway/README.md` — existing scaffolding, inert under
  ADR-0005.
- `CLAUDE.md` — absolute prohibitions #2 (Modal not public) and #8
  (no production deploy without approval).

## Addendum — 2026-05-23 (patent-portfolio anchoring)

A second operator verdict on the same proposal was delivered in Arabic
on 2026-05-23 (branch `claude/lexprim-fastapi-gateway-review-sHx1o`).
That verdict adds no new risks beyond the twelve mandatory constraints
above, but it anchors them to specific patent-portfolio items recorded
in `docs/audits/full-audit-2026-04-19.md` SECTION 2 and flags three
constraints that were implicit in the original ADR and are now made
explicit. This addendum does **not** supersede or relax any prior
constraint; it tightens the contract.

### Patent-portfolio anchoring (informational)

The twelve mandatory constraints map to these patent-portfolio items.
Implementation of each patent is recorded as `MISSING` in the cited
audit, so the anchoring is a **forward requirement**, not a claim of
current capability:

| Constraint | Patent anchor (per `docs/audits/full-audit-2026-04-19.md`) |
|---|---|
| #3 Ingress / #4 Auth | #10 SPIFFE zero trust (agent identity boundary) |
| #5 Data-classification gate | QAR-PAT-003 Sovereign Routing |
| #6 Registry adherence | #9 واجهة الوكلاء القانونية (registry-driven legal agents API) |
| #9 No file-path inputs | QAR-PAT-004 Pre-execution Security Gate |

Evidence label: `INFERRED` — anchoring is by operator verdict
(2026-05-23), not by code in this repository. The patents themselves
are catalogued as `MISSING` in the audit row, so this addendum cannot
claim the constraints are *implemented* — only that they are *required*
of any future FastAPI adapter.

### Constraint 13 — Pre-execution security gate (QAR-PAT-004)

Every adapter endpoint that accepts free-text prompts or file payloads
runs a pre-execution security gate **before** dispatch to any
provider. The gate enforces:

- **For uploads:** magic-byte plus MIME validation (already required by
  constraint #9). The allowed set is declared explicitly per endpoint;
  default-deny.
- **For prompts:** detection of prompt-injection patterns, jailbreak
  templates, and exfiltration directives. The mechanism is recorded
  in the adapter's `pre_execution_gate` module and is testable in
  isolation. A future implementation may use a CodeBERT-class
  classifier; the choice of model is not mandated by this ADR, only the
  existence of the gate and its unit-test coverage.

The gate **rejects** the request; it does not silently rewrite the
prompt. Rejections emit an audit event compatible with constraint #7.

### Constraint 14 — Agent-to-agent zero trust (patent #10)

When the adapter dispatches a request that produces a call to another
internal agent (Mihwar → Bayyinah, Bayyinah → validator, etc.), the
inner call carries:

- a caller-agent identity token (not the human caller's token alone),
- the original `data_classification`, unchanged,
- the original request ID,
- an audit trail entry recording the hop.

Inner agents authorize on the caller-agent identity. A call missing the
caller identity is refused, not defaulted to "trusted internal".

### Constraint 15 — Deterministic legal agents API (patent #9)

Adapter endpoints that return legal, regulatory, or
citation-bearing content must return, alongside the model output:

- the `source` (statute, ruling, document id),
- the `citation` text or paragraph reference,
- a `confidence` value the model would itself emit (no fabricated
  default of `1.0`).

Endpoints that cannot supply all three fields for a given response are
forbidden from labelling the response as legal/regulatory; the field
set becomes part of the endpoint's response contract, not a comment in
documentation. Until patent #9's runtime is in tree (currently
`MISSING`), legal-domain endpoints are **not** authorized on the
adapter at all.

### Bayyinah integration order (informational)

Per the operator verdict, when the adapter calls a Bayyinah workflow
that touches external systems, the integration order is: GitHub
first, then (per task type) Notion / Drive / Gmail / Figma /
Hugging Face / Cloudflare / GCP / Sentry. This is recorded for
reference; the adapter itself does not implement these integrations,
and naming endpoints after them without an implementation remains
forbidden by constraint #11.

## Execution Verdict (Addendum)

- **Status:** `CHANGED_BUT_NOT_VERIFIED`
- **Scope:** ADR-0006 only — three new constraints (#13, #14, #15) added; no code changed.
- **Canonical Path:** `docs/decisions/ADR-0006-fastapi-secondary-ai-gateway.md`
- **Files Touched:** `docs/decisions/ADR-0006-fastapi-secondary-ai-gateway.md`
- **Blockers:** none for the ADR itself; constraints #13–#15 cannot be tested until a FastAPI adapter is proposed.
- **Hot Surface Risk:** YES — tightening of the model-execution-path contract.
- **What Was Actually Changed:** Addendum dated 2026-05-23 added at end of ADR-0006: patent-portfolio anchoring table, constraints #13 (pre-execution security gate), #14 (agent-to-agent zero trust), #15 (deterministic legal agents API), Bayyinah integration order note.
- **What Was Actually Verified:** Patent items #9, #10, QAR-PAT-003, QAR-PAT-004 are catalogued as `MISSING` per `docs/audits/full-audit-2026-04-19.md` (VERIFIED 2026-05-23 by reading that file).
- **What Remains Unverified:** Every constraint in this ADR; no FastAPI adapter exists in tree to test against.
- **Next Valid Action:** Commit on `claude/lexprim-fastapi-gateway-review-sHx1o`, push, open draft PR referencing this addendum; do not propose adapter code until #13–#15 have test scaffolding.
