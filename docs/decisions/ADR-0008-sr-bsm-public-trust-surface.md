# ADR-0008 — SR.BSM Public Trust Surface Exception

- **Status:** Accepted
- **Decision date:** 2026-06-30
- **Decision owner:** CurLexAI platform operations
- **Related:** ADR-0001, ADR-0004, `render.yaml`, `public/trust/`, `scripts/render/serve-public.mjs`
- **Hot-surface classification:** YES — limited public surface and deployment blueprint exception

## Context

`CurLexAI/swarms` is an agent operations and control-plane repository. ADR-0001
forbids turning it into a public product monorepo, and ADR-0004 blocks product
shipping until canonical surfaces are resolved.

A narrow operational exception is needed for the Render service reported by the
operator:

- Render service name: `SR.BSM`
- Render service ID: `srv-d5uin6p4tr6s73e0d89g`
- Public domain: `www.lexprim.com`
- Internal address: `sr-bsm:10000`
- Runtime: Node
- Purpose: serve the static public trust surface only

Without an explicit ADR, changes to `public/` and `render.yaml` look like
ordinary product-surface drift. This ADR records why this exception is allowed
and where it stops.

## Evidence status

- `VERIFIED` — The operator provided the Render service name, service ID, public domain, and internal address used by this ADR.
- `VERIFIED` — The repository contains `public/trust/`, `render.yaml`, and `scripts/render/serve-public.mjs` as the bounded public trust surface implementation.
- `UNVERIFIED` — This ADR does not prove live Cloudflare, Render deployment, TLS, DNS, or production runtime readiness.
- `UNVERIFIED` — This ADR does not certify SAMA, NCA, PDPL, or product launch readiness.

## Decision

`SR.BSM` is accepted as an **operator public trust surface**, not as the
LexPrim/Qarar product frontend and not as a public API.

The exception permits only the following repository changes:

1. `public/trust/**` static trust-center assets.
2. `scripts/render/serve-public.mjs` as a minimal Node static adapter.
3. `render.yaml` entries required to deploy the static trust surface on the
   named Render service.
4. Tests that prove the public adapter is static, bounded, and does not expose
   backend agent runtimes.
5. Operations documentation describing the boundary.

## Mandatory constraints

1. `SR.BSM` must not expose Modal, Mihwar, Bayyinah, MCP, RAG, private agent,
   or product API endpoints.
2. `SR.BSM` must not accept customer data, user prompts, credentials, files,
   or legal/regulatory payloads.
3. The public surface must remain static or health-check only.
4. `healthCheckPath` may expose service liveness only; it must not expose
   runtime readiness, secret presence, endpoint URLs, or model availability.
5. Any future addition of forms, dashboards, auth flows, REST APIs, GraphQL,
   websocket channels, upload endpoints, or model invocation requires a new ADR.
6. Cloudflare, Render, Vercel, and Modal status must not be treated as proof of
   SAMA/NCA/PDPL compliance without external evidence.

## Allowed paths

| Path | Status | Notes |
| --- | --- | --- |
| `public/trust/**` | Allowed | Static trust surface only. |
| `scripts/render/serve-public.mjs` | Allowed | Static adapter and `/healthz` only. |
| `tests/renderPublicServer.test.js` | Allowed | Boundary tests for public adapter. |
| `render.yaml` | Allowed by this ADR | Only for `SR.BSM` public trust surface configuration. |
| `.github/workflows/render-preflight.yml` | Allowed by this ADR | May validate `SR.BSM` static service package. |

## No-touch paths without a future ADR

| Path or surface | Reason |
| --- | --- |
| `public/index.html` | Would create a generic product homepage in the control-plane repo. |
| `public/about`, `public/contact`, `public/privacy`, `public/terms` | Product/marketing surface drift. |
| `src/routes/**`, `src/api/**`, `backend_fastapi/**` | Public API or product runtime drift. |
| `.agents/modal_app.py` public exposure | Modal remains backend-only. |
| Browser-callable Mihwar/Bayyinah/MCP endpoints | Violates backend-only agent boundary. |

## Security requirements

The public adapter must preserve:

- path traversal blocking,
- no secret or endpoint disclosure,
- no request body processing,
- security headers for frame, referrer, content type, permissions, and CSP,
- `/healthz` returning only non-sensitive liveness metadata,
- tests covering root mapping, health, 404, traversal, and content types.

## Consequences

- `SR.BSM` may be deployed from this repository only as a trust surface.
- The repository remains an agent operations repository.
- The exception does not promote `CurLexAI/swarms` to the canonical LexPrim
  product frontend repository.
- Future public product work remains blocked until a separate canonical surface
  decision supersedes ADR-0004.
