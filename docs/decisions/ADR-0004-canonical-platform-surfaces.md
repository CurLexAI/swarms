# ADR-0004 — Canonical Platform Surfaces and Duplicate Deploy Quarantine

- **Status:** Accepted
- **Decision date:** 2026-05-31
- **Decision owner:** CurLexAI platform operations
- **Supersedes:** none
- **Related:** `docs/decisions/ADR-0001-swarms-boundary.md`

## Context

CurLexAI platform work currently has a surface-canonicalization risk: the
control-plane repository, frontend candidates, Vercel projects, Render service,
Modal runtime, and Cloudflare edge can be mistaken for interchangeable product
surfaces.

That ambiguity is more dangerous than an ordinary product bug because it can
cause engineers or coding agents to:

- Edit a mirrored or non-canonical repository.
- Deploy from a prototype or legacy Vercel project.
- Treat the `swarms` control-plane repository as a public product monorepo.
- Expose private Modal runtime paths to browser or iPhone surfaces.
- Interpret Cloudflare edge health as proof of backend or product readiness.

`CurLexAI/swarms` is already bounded by ADR-0001 as the operations,
validation, and sovereign data pipeline layer. This ADR extends that boundary
with an explicit canonical surface map and a freeze on duplicate deploy
surfaces.

## Decision

Product shipping is blocked until surface canonicalization is complete.

**NO PRODUCT SHIP UNTIL SURFACE CANONICALIZATION IS DONE.**

The approved workstream is control-plane cleanup only:

1. Maintain a platform surface registry.
2. Maintain a Vercel surface registry.
3. Quarantine duplicate repository and Vercel candidates.
4. Keep `CurLexAI/swarms` as the canonical control-plane repository only.
5. Require a future evidence-backed decision before product deployment resumes.

## Canonical Surface Map

| Surface | Source of truth | Decision |
|---|---|---|
| Control plane / agents / gates | `CurLexAI/swarms` | Canonical operations repository only. |
| Public website / frontend | TBD | No deployment until one canonical repository is selected. |
| Vercel production app | TBD between `lexnexus` and `lex-nexus` | Freeze production aliases until one canonical project is selected. |
| Render MCP Gateway | `render.yaml` inside `CurLexAI/swarms` | Preflight and manual deploy only; not a public product API. |
| Modal runtime | Backend-only private runtime | Must not be called directly from browsers, iPhone clients, or public frontend code. |
| Cloudflare | DNS / TLS / WAF edge | Edge layer only; not runtime-readiness evidence. |

## Repository Decisions

`CurLexAI/swarms` remains the canonical control-plane repository. It may hold
agents, gates, policies, MCP glue, Modal backend-only glue, and sovereign
private pipelines.

`CurLexAI/swarms` must not become a product monorepo. It must not add public
frontend surfaces, marketing pages, customer dashboards, browser-callable APIs,
or public REST / GraphQL product contracts.

`CurLexAI/FRONT` and `CurLexAI/website-` are treated as quarantined until proven
otherwise. They must not be used for development or deployment until their
README files carry a quarantine banner and an audit identifies whether either
is a real frontend or only a duplicate control-plane mirror.

## Vercel Decisions

Production aliases are frozen until one canonical project is selected and
recorded in `docs/operations/vercel-surface-registry.md`.

`lexnexus` is a candidate canonical project only after audit. `lex-nexus` is a
suspect, legacy, or marketing-prototype candidate until audit proves otherwise.
Duplicate or ambiguous projects such as `wejdan-ai`, `chatbot-ui`,
`nextjs-ai-chatbot*`, `ai-orchestrator`, `rsc-genui`, and
`morphic-ai-answer-engine-generative-ui` must not receive production aliases
unless promoted by a future decision.

## Consequences

- Agents must reject product-facing changes in `CurLexAI/swarms` unless a
  future ADR changes the repository boundary.
- Deployment fixes must name the target surface and prove it is canonical.
- Render MCP Gateway work remains infrastructure/control-plane work, not
  product API work.
- Modal endpoints remain backend-only and private.
- Cloudflare checks can support edge validation but cannot prove application
  runtime readiness.
- Product release waits; control-plane cleanup proceeds.

## Acceptance Criteria

This ADR is satisfied when:

1. `docs/operations/platform-surface-registry.md` exists and records the
   current surface map.
2. `docs/operations/vercel-surface-registry.md` exists and records the Vercel
   freeze policy.
3. No production code, CI/CD workflow, secret, or deployment configuration is
   changed by the canonicalization PR.
4. A future PR is required to promote any frontend repository or Vercel project
   to canonical production status.
