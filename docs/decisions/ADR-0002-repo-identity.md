# ADR-0002: Repository Identity Enforcement for CurLexAI/swarms

- Status: Accepted
- Date: 2026-05-08
- Decision Owners: Repository maintainers

## Context

CurLexAI/swarms is defined by governance documents as an **agent operations and validation repository**.
However, the current tree still contains product-facing UI and control-plane application surfaces.
This mismatch creates architectural drift and causes boundary gates to fail consistently.

## Decision

CurLexAI/swarms is explicitly constrained to **operations-only** scope.

The following product-facing surfaces are out of scope for this repository and must be migrated to the application repository:

- `public/index.html`
- `public/control/`
- `src/control-hub/`
- `src/apiSecurity.js`

## Consequences

1. Boundary gates remain authoritative and should continue to block product-surface drift in this repository.
2. Work on UI/control runtime code proceeds only in the product repository after migration.
3. PRs touching operations-only code can be evaluated independently from product runtime concerns.

## Plan of Record

1. Submit a dedicated cleanup PR that removes or migrates the out-of-scope surfaces listed above.
2. Re-run repository checks after cleanup to confirm boundary-gate convergence.
3. Rebase pending technical PRs (e.g., TypeScript/runtime hardening) on top of the cleaned boundary state.
