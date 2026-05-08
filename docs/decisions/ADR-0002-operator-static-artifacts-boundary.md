# ADR-0002 — Operator-Only Static Artifacts Boundary

- **Status:** Accepted
- **Decision date:** 2026-05-08
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none

## Context

`public/index.html`, `public/trust/*`, and `public/control/*` exist in `CurLexAI/swarms`.
This can be misread as product-web ownership unless the boundary is explicit and
enforceable.

ADR-0001 already defines `swarms` as an agent-operations repository. This ADR
adds a specific carve-out and enforcement rules for the current `public/*`
content.

## Decision

The `public/` tree in `CurLexAI/swarms` is restricted to **operator-only static
artifacts** used for agent operations visibility and trust documentation.

Allowed operator surfaces:

- `public/index.html` (operator landing page for repository operations context).
- `public/trust/*` (operator trust and policy publication artifacts).
- `public/control/*` (operator command/control static UI for repository-level
  operations only).

These files are **not** product application surfaces and must not contain:

- product account/authentication flows,
- product API integration paths,
- customer data processing UX,
- product marketing or sales pages,
- product runtime embedding/feature UI.

## Ownership

- Primary owner: repository operator for `CurLexAI/swarms`.
- Enforcement owner: CI boundary gates under `scripts/commander/` and
  `.github/workflows/agent-review.yml`.

## Security Controls

1. Any new directory under `public/` is blocked by default unless explicitly
   approved via ADR marker.
2. Any change that introduces product-like surfaces under `public/` is rejected.
3. Boundary checks run in CI before secret-dependent review steps.

## ADR Approval Marker

To add a new approved public operator surface, a pull request must include an
explicit marker in commit message or PR body:

- `ADR_APPROVED: ADR-XXXX`

where `ADR-XXXX` maps to an accepted ADR file under `docs/decisions/`.

## Acceptance Limits

This ADR does **not** authorize migration of product/application code into
`swarms`. Product web surfaces remain out-of-scope and must live in the
application repository.

## Consequences

- Unapproved additions under `public/` fail CI.
- Existing allowed roots are narrowly scoped to `index.html`, `trust`, and
  `control`.
- Expansion requires a new ADR and explicit approval marker.
