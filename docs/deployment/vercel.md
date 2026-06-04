# Vercel Deployment Contract

## Scope

The canonical frontend entrypoint in this repository is the static Trust Center at `public/trust/index.html`.
No Next.js, Vite, Remix, or application frontend has been scaffolded in this repository.

Vercel must deploy only the existing static `public/` surface. Product application code remains out of scope until a real frontend source tree is intentionally recovered or supplied.

## GitHub Secrets Contract

The Vercel workflow expects these names to be configured in GitHub Secrets before deployment jobs can run:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

Do not commit Vercel token values, organization IDs, project IDs, deploy hooks, or generated `.vercel/` metadata.

## Public Environment Contract

Only variables with public frontend prefixes may be exposed to browser code. In this repository, public frontend configuration starts with `NEXT_PUBLIC_`.

Private runtime variables such as `MIHWAR_ENDPOINT`, `BAYYINAH_ENDPOINT`, endpoint-specific runtime tokens, Modal tokens, Render deploy hooks, and provider API tokens must remain server-side secrets.

## Modal Boundary

Public frontend code must never call Modal/private agent endpoints directly, including `*.modal.run` URLs or the Modal SDK.
All agent execution must flow through approved server-side control-plane relays with authentication, validation, audit logging, and human review where required.

The Vercel workflow runs `scripts/commander/modal-boundary-gate.sh` before deploy jobs to enforce this boundary for public/client surfaces.
