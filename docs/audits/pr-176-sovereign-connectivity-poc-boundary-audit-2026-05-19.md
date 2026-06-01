# Boundary Audit — PR #176 `sovereign-connectivity-poc/`

- **Audit date:** 2026-05-19
- **Author:** Go-live monitoring session (`claude/golive-monitoring-c5hLy`)
- **Subject PR:** [CurLexAI/swarms#176](https://github.com/CurLexAI/swarms/pull/176) — *Add one-day Sovereign Connectivity PoC monorepo*
- **PR state at audit time:** merged 2026-05-19T21:18:57Z by `Mihwer` (squash merge of `codex/build-typescript-monorepo-for-connectivity-poc`)
- **Merge commit:** `a791273`
- **Disposition:** **REPORT ONLY** — no rollback, no gate change, no file removal performed by this audit.

## Scope

Audit the merged contents of `sovereign-connectivity-poc/` against
[ADR-0001 — Repository Boundary](../decisions/ADR-0001-swarms-boundary.md)
to record whether the merge constitutes boundary drift, an intentional
exception, or a permitted sovereign-data-pipeline addition. Per the
operator's direction this is investigation only; remediation decisions
remain with the operator.

## Method

Read-only inspection of the merged tree, the ADR-0001 forbidden-additions
table, the `scripts/commander/adr-0001-boundary-gate.sh` literal
`FORBIDDEN_PATHS` array, and the merged PR description and metadata.
No code, configuration, or gate was modified during the audit.

## Findings

### Finding 1 — Public Fastify REST surface bound to all interfaces

- **Evidence (VERIFIED):** `sovereign-connectivity-poc/apps/api/src/server.ts:52-57`
  unconditionally calls
  `buildServer().listen({ port: 3000, host: '0.0.0.0' })` outside test
  mode. Routes defined: `POST /telemetry`, `POST /decision`,
  `GET /devices/:id/status`, `GET /audit`.
- **ADR-0001 text (VERIFIED):** Forbidden-additions table, rows
  *"Public-facing web app (Express / Fastify / Next.js / Vite / React
  routes)"* and *"Public REST or GraphQL API surfaces"*.
- **Verdict (INFERRED):** Matches both forbidden categories on the
  literal wording of ADR-0001. No allowed-additions row covers a
  publicly-bound Fastify listener.

### Finding 2 — Qarar policy source under repository root

- **Evidence (VERIFIED):** `sovereign-connectivity-poc/packages/policy/src/index.ts`
  implements `decide(telemetry)` returning Qarar-style decisions
  (`decisionId`, `action`, `reason`, `riskLevel`) with reasons authored
  in Arabic and SA-country gating logic.
- **ADR-0001 text (VERIFIED):** Forbidden-additions table, row
  *"Importing LexPrim or Qarar source files into this repo without a
  documented intake plan"*.
- **Verdict (INFERRED):** Matches the literal wording. No intake plan
  for Qarar product source exists in `docs/decisions/` or `docs/audits/`
  prior to this audit. The PR description does not cite an intake ADR.

### Finding 3 — Backend service surface via docker-compose

- **Evidence (VERIFIED):** `sovereign-connectivity-poc/docker-compose.yml`
  exposes a service `mihwar-api` on port `3000:3000` that runs
  `pnpm --filter @poc/api dev`.
- **ADR-0001 text (VERIFIED):** Forbidden-additions table, row
  *"New backend services (`backend_fastapi`, persistent stores, message
  queues) that expose product runtime behavior"*.
- **Verdict (INFERRED):** Matches the spirit of the prohibition. The
  service is explicitly published on a host port.

### Finding 4 — Gate did not trip because path is not enumerated

- **Evidence (VERIFIED):** `scripts/commander/adr-0001-boundary-gate.sh`
  `FORBIDDEN_PATHS` array (lines 18-32) lists `backend_fastapi`,
  `src/routes`, `src/pipeline`, `src/factory`, `src/control-hub`,
  `src/api`, `src/apiSecurity.js`, `public/index.html`, `public/about`,
  `public/contact`, `public/privacy`, `public/terms`. It does not list
  `sovereign-connectivity-poc` or any `apps/api`-style alias.
- **Verdict (VERIFIED):** Literal-path enumeration is why the gate did
  not block this merge. ADR-0001's forbidden categories are described
  by *kind* (e.g. "public REST surface"), but the gate enforces them by
  *path*. The two diverged for this PR.

### Finding 5 — Build artifacts committed

- **Evidence (VERIFIED):** Merged tree includes
  `sovereign-connectivity-poc/dist/` (`.d.ts` files) and
  `sovereign-connectivity-poc/packages/shared/tsconfig.tsbuildinfo`.
- **Note (INFERRED):** Per repository conventions and CLAUDE.md
  ("Do not commit `node_modules`, build output, caches, or opaque
  generated bundles as source"), build output should not be committed.
  Separate from boundary drift, but worth flagging in the same audit.

## What was NOT verified

- Whether the operator has an out-of-band decision to carve out
  `sovereign-connectivity-poc/` as an approved exception. No such ADR
  or amendment exists under `docs/decisions/` as of this audit.
- Whether the windows-agent code (`apps/windows-agent/`) introduces
  additional surfaces beyond the API; only the API entry points were
  read for this pass.
- Runtime behavior. No build, install, or run was attempted by this
  audit. All evidence is static-source inspection.

## Recommended next valid actions (operator decision)

The audit does not select between these. They are listed so the
operator can choose:

1. **Codify the exception.** Author a successor ADR (e.g. ADR-0005)
   that records the operator's decision to allow
   `sovereign-connectivity-poc/` as a time-boxed PoC carve-out from
   ADR-0001, with explicit expiry conditions and a sunset plan.
2. **Restore the boundary.** Move the PoC into a separate repository
   (per ADR-0001's own guidance that public application runtime
   belongs outside `swarms`), and remove the directory from `main`
   here.
3. **Tighten the gate.** Update `scripts/commander/adr-0001-boundary-gate.sh`
   to enforce ADR-0001 by *kind* rather than by literal path —
   e.g. scan for Fastify/Express imports outside `.agents/`, scan for
   `listen({` calls on `0.0.0.0`, or add `sovereign-connectivity-poc`
   to `FORBIDDEN_PATHS` if option (2) is chosen.
4. **Remove build artifacts.** Independent of boundary disposition,
   remove `sovereign-connectivity-poc/dist/` and `*.tsbuildinfo` from
   the repository and add appropriate `.gitignore` entries.

## Status labels

- Audit status: VERIFIED for static-source claims, INFERRED for
  ADR-mapping verdicts.
- Action status: SKIPPED_UNVERIFIED — no remediation performed.
- Repository state at audit completion: unchanged.
