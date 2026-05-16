# ADR-0001 — `CurLexAI/swarms` Repository Boundary

- **Status:** Accepted
- **Decision date:** 2026-05-08
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none

## Context

Recurring agent and human work on `CurLexAI/swarms` has assumed, incorrectly,
that this repository is the monorepo for the LexPrim / Qarar application
(routes, frontend pages, public API surfaces, agent registry of 100+ entries).
It is not.

`README.md` and `AGENTS.md` already state this in operating-language form:
> "agents must treat the repository as an **agent operations repository**, not
> as a recovered application monorepo."

But that statement lives inside long handbooks. Multiple planning sessions
have nonetheless proposed adding `src/routes/*.js`, marketing pages (`/about`,
`/contact`, `/privacy`, `/terms`), public REST surfaces, embedded product UI,
and large agent registries with `autoStart` flags. None of those belong here.
Without a single, citeable boundary record, the next agent or session repeats
the same misunderstanding.

A second reality also now exists: the separate LexPrim application repository
is no longer available as the home for sovereign regulatory ingestion and
retrieval work. That made the earlier blanket prohibition on all RAG-oriented
code too coarse. The boundary needs to distinguish between prohibited product
surfaces and permitted sovereign data pipelines that stay inside the private
Modal/Qdrant operating layer.

This ADR is that record.

## Decision

`CurLexAI/swarms` is the **agent operations, validation, and sovereign data
pipeline layer** for the CurLexAI program. It is explicitly **not** a general
LexPrim / Qarar public application monorepo.

The repository contents are constrained to five functional categories:

1. **Agent operations.** Catalog, configuration, providers (Modal /
   OpenAI / Anthropic), router, and validators that describe *how* coding
   agents (Mihwar, Bayyinah, Copilot SWE) are invoked.
2. **Modal runtime glue.** `.agents/modal_app.py` and adjacent files that
   define the Modal deployment surface for those agents. Modal endpoints,
   tokens, and deploy steps are operated outside this repo.
3. **Validation gates.** Python tests under `tests/`, JavaScript tests for
   the unified agent adapter, and shell gates under `scripts/commander/`
   (modal-boundary, p0-security, agent-presence, codex-commander).
4. **Skills, policies, and operations docs.** `.agents/skills/`,
   `.agents/policies/`, `docs/operations/`, `docs/audits/`, and similar
   documentation of how this layer is operated.
5. **Sovereign data pipelines.** Private ingestion, embedding, and vector
   search code that remains inside the Modal-sovereign operating layer and
   does not create a public application surface.

Anything that does not fit one of those five categories does not belong in
this repository.

## Forbidden additions

The following must not be introduced into `CurLexAI/swarms`. Each prohibition
exists to prevent a specific recurring failure mode:

| Forbidden category | Reason |
|---|---|
| Public-facing web app (Express / Fastify / Next.js / Vite / React routes) | Confuses repo identity; route auth and surface area belong in the application surface, not the swarms control layer. |
| Product source that exposes customer-facing workflows, dashboards, page templates, or marketing pages | Entangles operator code with public product UX and weakens provenance boundaries. |
| Public REST or GraphQL API surfaces | This repo is not the public application runtime; an exposed surface here would be a phantom or mis-scoped service. |
| External vector stores or non-sovereign retrieval backends for regulated data | Violates the sovereign-boundary intent for regulatory data handling. |
| `autoStart` / always-on activation flags on agents or pipelines | Activation policy is a runtime decision in the application or Modal layer, not a swarms-level commitment. |
| New backend services (`backend_fastapi`, persistent stores, message queues) that expose product runtime behavior | Same boundary reason as application code. |
| Importing LexPrim or Qarar source files into this repo without a documented intake plan | Bypasses the controlled-intake protocol described in `AGENTS.md`. |
| Production-readiness claims, regulatory-compliance claims, or runtime-activation claims without smoke-test evidence | Already prohibited by `AGENTS.md` "Absolute Prohibitions"; restated here as a boundary item because every drift attempt has been accompanied by an unsupported readiness claim. |

If a future task requires any of the above, it must be staged in the
appropriate surface with explicit operator approval, not merged silently as
ordinary swarms work.

## Allowed additions

Changes inside `CurLexAI/swarms` should fit one of:

- New or updated Python / Node / Shell **validation gates** under `tests/`,
  `scripts/commander/`, or `.agents/validators/`.
- New or updated **agent operating doctrine** under `.agents/skills/`,
  `.agents/policies/`, or `docs/operations/`.
- Additions or updates to `.agents/config/agents.yaml`, `.agents/modal_app.py`,
  `.agents/invoke.py`, `.agents/pr_review.py`, `.agents/validate.py`, or
  their adapters under `src/services/`.
- **Sovereign data pipeline code** under `.agents/` or `.agents/pipelines/`
  for ingestion, embedding, retrieval, and verification, provided that it:
  - runs only on Modal or other operator-approved private runtime surfaces,
  - uses sovereign backends for regulated data,
  - exposes no public/client route or browser-callable product API,
  - introduces no `autoStart` activation,
  - passes `scripts/commander/modal-boundary-gate.sh .`.
- Documentation updates: `AGENTS.md`, `README.md`, `docs/decisions/` (ADRs),
  `docs/audits/`, `docs/launch-evidence/`, `docs/secrets-policy.md`.
- Test dependencies and runtime requirement files used by the agent
  validation gates and sovereign pipeline checks (`requirements-agent.txt`,
  `package.json`, `tsconfig.json`).

## Sanctioned exception record

The first use of the new sovereign-data-pipeline category is the operator-
approved POC merged on 2026-05-16:

- `.agents/ingest_test.py`
- `requirements-agent.txt` additions for `qdrant-client` and `FlagEmbedding`
- Tracking issue: `#158`

This POC is allowed because it stays inside Modal, targets a Modal-sovereign
Qdrant instance, exposes only bearer-protected private endpoints, and carries
explicit POC labeling. It does **not** by itself establish production
readiness.

## Consequences

- Any PR that introduces forbidden categories above must be rejected at
  review and not merged, regardless of code quality.
- Repository validation gates must continue to pass before claiming
  operational readiness. The canonical command list is documented in
  `README.md` under "Local verification".
- Sovereign data pipeline work is allowed only while it remains private,
  operator-scoped, and free of public runtime surfaces.
- This boundary is descriptive of the current state, not aspirational. If
  the program later rebuilds a separate public application repository or
  decides to move public product runtime back out of `swarms`, that requires
  a successor ADR rather than silent drift.
- Cross-surface work that needs both swarms and a future public application
  repo must be staged across separate changes with explicit cross-references.

## Verification

This ADR is satisfied while:

- `python3 -m py_compile .agents/*.py` passes.
- `python3 .agents/validate.py` passes.
- `python3 .agents/invoke.py info` passes and lists only configured agents.
- `python3 -m unittest discover -s tests` passes.
- `python3 -m pytest -q tests/` passes (after
  `pip install -r requirements-agent.txt`).
- `npm test` passes against the unified agent adapter Node test suite.
- `scripts/commander/modal-boundary-gate.sh .` reports no leakage of
  Modal endpoints into public-facing surfaces.
- `scripts/commander/adr-0001-boundary-gate.sh .` reports no forbidden
  public/product surfaces or `autoStart` drift.
- Any sovereign data pipeline remains under `.agents/` or `.agents/pipelines/`
  and does not add public routes or non-sovereign regulated-data backends.

`npx tsc --noEmit` is also part of the validation set, but currently has a
known pre-existing strict-mode blocker (`TS2307: Cannot find module
'../runners/agentRunner.js'` in `src/services/unifiedAgentAdapter.ts`).
That blocker is tracked separately and does not weaken this ADR.
