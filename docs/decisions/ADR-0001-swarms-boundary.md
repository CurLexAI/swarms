# ADR-0001 — `CurLexAI/swarms` Repository Boundary

- **Status:** Accepted
- **Decision date:** 2026-05-08
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none

## Context

Recurring agent and human work on `CurLexAI/swarms` has assumed, incorrectly,
that this repository is the monorepo for the LexPrim / Qarar application
(routes, frontend pages, RAG pipelines, public API surfaces, agent registry
of 100+ entries). It is not.

`README.md` and `AGENTS.md` already state this in operating-language form:
> "agents must treat the repository as an **agent operations repository**, not
> as a recovered application monorepo."

But that statement lives inside long handbooks. Multiple planning sessions
have nonetheless proposed adding `src/routes/*.js`, `src/pipeline/qarar-rag-infra.py`,
marketing pages (`/about`, `/contact`, `/privacy`, `/terms`), embedded RAG
infrastructure, and large agent registries with `autoStart` flags. None of
those belong here. Without a single, citeable boundary record, the next agent
or session repeats the same misunderstanding.

This ADR is that record.

## Decision

`CurLexAI/swarms` is the **agent operations and validation layer** for the
CurLexAI program. It is explicitly **not** the LexPrim / Qarar application.

The repository contents are constrained to four functional categories:

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

Anything that does not fit one of those four categories does not belong in
this repository.

## Forbidden additions

The following must not be introduced into `CurLexAI/swarms`. Each prohibition
exists to prevent a specific recurring failure mode:

| Forbidden category | Reason |
|---|---|
| Public-facing web app (Express / Fastify / Next.js / Vite / React routes) | Confuses repo identity; route auth and surface area belong in the application repo. |
| LexPrim / Qarar product source (RAG pipelines, embedding workers, page templates, marketing pages, dashboards) | Weakens patent and provenance evidence stored elsewhere; entangles two release cycles. |
| Public REST or GraphQL API surfaces | This repo has no application runtime; an exposed surface here would be a phantom service. |
| `autoStart` / always-on activation flags on agents | Activation policy is a runtime decision in the application or Modal layer, not a swarms-level commitment. |
| New backend services (`backend_fastapi`, persistent stores, message queues) | Same boundary reason as application code. |
| Importing LexPrim or Qarar source files into this repo without a documented intake plan | Bypasses the controlled-intake protocol described in `AGENTS.md`. |
| Production-readiness claims, regulatory-compliance claims, or runtime-activation claims without smoke-test evidence | Already prohibited by `AGENTS.md` "Absolute Prohibitions"; restated here as a boundary item because every drift attempt has been accompanied by an unsupported readiness claim. |

If a future task requires any of the above, it must be staged in the
appropriate application repository, not here.

## Allowed additions

Changes inside `CurLexAI/swarms` should fit one of:

- New or updated Python / Node / Shell **validation gates** under `tests/`,
  `scripts/commander/`, or `.agents/validators/`.
- New or updated **agent operating doctrine** under `.agents/skills/`,
  `.agents/policies/`, or `docs/operations/`.
- Additions or updates to `.agents/config/agents.yaml`, `.agents/modal_app.py`,
  `.agents/invoke.py`, `.agents/pr_review.py`, `.agents/validate.py`, or
  their adapters under `src/services/`.
- Documentation updates: `AGENTS.md`, `README.md`, `docs/decisions/` (ADRs),
  `docs/audits/`, `docs/launch-evidence/`, `docs/secrets-policy.md`.
- Test dependencies and runtime requirement files used by the agent
  validation gates (`requirements-agent.txt`, `package.json`,
  `tsconfig.json`).

## Consequences

- Any PR that introduces forbidden categories above must be rejected at
  review and not merged, regardless of code quality.
- Repository validation gates must continue to pass before claiming
  operational readiness. The canonical command list is documented in
  `README.md` under "Local verification".
- This boundary is descriptive of the current state, not aspirational. If
  the program decides to relocate the LexPrim / Qarar application *into*
  this repository, that is a deliberate decision and requires a successor
  ADR that supersedes this one — not a silent merge.
- Cross-repository work that requires both swarms and the application repo
  must be staged across two PRs, one in each repo, with explicit
  cross-references.

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
  application-repo surfaces or `autoStart` drift.
- The four `Forbidden additions` categories above are absent from the tree.

`npx tsc --noEmit` is also part of the validation set, but currently has a
known pre-existing strict-mode blocker (`TS2307: Cannot find module
'../runners/agentRunner.js'` in `src/services/unifiedAgentAdapter.ts`).
That blocker is tracked separately and does not weaken this ADR.
