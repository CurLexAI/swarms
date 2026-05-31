# Platform Surface Registry

- **Status:** Active control-plane registry
- **Owner:** CurLexAI platform operations
- **Last reviewed:** 2026-05-31
- **Decision record:** `docs/decisions/ADR-0004-canonical-platform-surfaces.md`

## Executive Decision

**NO PRODUCT SHIP UNTIL SURFACE CANONICALIZATION IS DONE.**

The platform must not ship product-facing changes while repository ownership,
Vercel project ownership, deployment aliases, and runtime boundaries remain
ambiguous. The current safe workstream is control-plane cleanup only.

## Evidence Labels

This registry follows the repository evidence taxonomy:

- `VERIFIED` — confirmed by observable repository content or command output.
- `INFERRED` — reasonable conclusion from available evidence, but not directly
  confirmed in this repository.
- `UNVERIFIED` — not checked, outside this repository, or blocked by missing
  access, secrets, or runtime evidence.

## Canonical Surface Map

| Surface | Source of truth | Status | Decision |
|---|---|---|---|
| Control plane / agents / gates | `CurLexAI/swarms` | `VERIFIED` | Canonical operations repository only. |
| Public website / frontend | TBD | `UNVERIFIED` | No deployment until one canonical frontend repository is selected and audited. |
| Vercel production app | TBD between `lexnexus` and `lex-nexus` | `UNVERIFIED` | Freeze production aliases until one canonical project is selected. |
| Render MCP Gateway | `render.yaml` in `CurLexAI/swarms` | `VERIFIED` | Preflight and manual deploy only; not a public product API. |
| Modal runtime | Backend-only private runtime | `VERIFIED` | Must not be exposed to browsers, iPhone clients, or public frontend code. |
| Cloudflare | DNS / TLS / WAF edge | `INFERRED` | Edge posture only; not evidence of product runtime health. |

## Repository Classification

| Repository | Classification | Evidence label | Decision |
|---|---|---|---|
| `CurLexAI/swarms` | Canonical control-plane repository | `VERIFIED` | Keep as agents, gates, policies, MCP, Modal glue, and sovereign private pipelines. |
| `CurLexAI/FRONT` | Duplicate or non-canonical surface | `UNVERIFIED` | Quarantine before any deploy or development use. |
| `CurLexAI/website-` | Duplicate or non-canonical surface | `UNVERIFIED` | Quarantine before any deploy or development use. |
| `CurLexAI/qaraar-app` or `CurLexAI/qaraar-web` | Proposed future public app name | `UNVERIFIED` | Candidate naming pattern only; create/select only after audit. |
| `CurLexAI/qaraar-api` | Proposed future product API name | `UNVERIFIED` | Candidate only if a separate product API is required. |
| `CurLexAI/qaraar-infra` | Proposed future infrastructure registry | `UNVERIFIED` | Candidate only if Terraform / Cloudflare / Vercel registry ownership is separated. |

## `swarms` Boundary

`CurLexAI/swarms` is a control-plane and operations repository. It may contain:

- Agent profiles, registries, adapters, and validation gates.
- Repository policies, skills, review automation, and MCP glue.
- Render MCP Gateway configuration and preflight documentation.
- Modal backend-only glue for private Mihwar and Bayyinah runtime paths.
- Sovereign private pipelines that do not create a public product surface.

It must not contain:

- Public frontend routes or marketing pages.
- Customer dashboards or browser-callable product behavior.
- Public REST or GraphQL product APIs.
- Product runtime services that are deployable as customer-facing surfaces.
- Deployment changes that route production aliases before canonicalization.

## Duplicate Repository Quarantine Requirement

The following banner must be added at the top of the `README.md` in every
non-canonical duplicate repository before anyone uses it for development or
publishing:

```markdown
# QUARANTINED — Not canonical
This repository is not the canonical frontend or website surface.
Do not deploy from this repository.
Canonical control-plane repository: CurLexAI/swarms.
Canonical public frontend: TBD.
```

This `swarms` PR records the requirement only. It does not edit external
repositories.

## Product-Change Gate

Until this registry and the Vercel Surface Registry identify a canonical
frontend and production Vercel project, agents and humans must reject:

1. Product-facing changes inside `CurLexAI/swarms`.
2. Vercel production alias changes for non-canonical projects.
3. Placeholder deployment fixes that do not name the target surface.
4. Browser or iPhone access paths to Modal private runtime endpoints.
5. Claims that Cloudflare health proves application runtime readiness.

## Implementation Order

1. Maintain this platform surface registry.
2. Quarantine duplicate repositories (`FRONT`, `website-`) outside this PR.
3. Freeze Vercel production aliases until canonical ownership is recorded.
4. Select and audit one canonical frontend repository and Vercel project.
5. Harden Render MCP preflight without promoting it to a public product API.
6. Unify runtime policies after surface ownership is clear.
7. Resume product shipping only after canonicalization is complete.
