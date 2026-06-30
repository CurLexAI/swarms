# Change vs No-Touch Guide

Date: 2026-06-30
Scope: `CurLexAI/swarms` as an agent operations and sovereign control-plane repository.

## Purpose

This guide defines what contributors and automated agents may change safely,
what requires ADR review, and what must not be touched without explicit owner
approval.

## Safe zones

Changes in these areas are generally allowed when they are small, tested, and
consistent with ADR-0001:

| Area | Allowed examples | Required checks |
| --- | --- | --- |
| `.agents/config/**` | Agent metadata, model IDs, routing config. | `.agents/validate.py`, agent presence gate. |
| `.agents/providers/**` | Provider adapters and mocks. | Unit tests, no secret logging, no default external egress. |
| `.agents/validators/**` | Input/output validation, redaction, audit guards. | Positive and negative tests. |
| `scripts/commander/**` | CI gates and operator diagnostics. | Shell syntax, targeted gate execution. |
| `scripts/ci/**` | CI orchestration wrappers. | Fail-closed tests, no secret printing. |
| `tests/**` | Unit, integration, policy, and boundary tests. | Test suite must pass or document blockers. |
| `docs/operations/**` | Runbooks, evidence reports, handoffs. | Evidence labels for readiness claims. |
| `docs/audits/**` | Audit outputs and findings. | No raw secret values. |

## Conditional zones requiring ADR or explicit architecture approval

| Area | Why sensitive | Minimum approval evidence |
| --- | --- | --- |
| `public/**` | Changes public surface exposed to users. | Accepted ADR or explicit approved exception such as ADR-0008. |
| `render.yaml` | Changes deployment topology. | Render service evidence, rollback path, preflight update. |
| `.github/workflows/**` | Changes CI permissions or deployment behavior. | Least privilege, fail-closed behavior, tests. |
| `src/runtime-policy.ts` | Changes model/data routing behavior. | Runtime policy tests and threat impact note. |
| `src/policy/**` | Changes sovereign policy decisions. | Classification tests and no downgrade. |
| `docker-compose*.yml` | Changes network/service topology. | Threat model and port exposure review. |
| `.agents/modal_app.py` | Changes private model runtime endpoints. | Modal boundary tests and endpoint smoke plan. |

## No-touch zones without a new ADR

| Area | Reason |
| --- | --- |
| Product pages beyond `public/trust/**` | Would turn the repo into a product/marketing frontend. |
| Public REST/GraphQL APIs | Violates swarms repository boundary. |
| Browser-callable Modal/Mihwar/Bayyinah endpoints | Violates backend-only agent boundary. |
| Real `.env` files or secret values | Violates secrets boundary. |
| Build artifacts, `node_modules`, generated bundles | Supply-chain and provenance risk. |
| `autoStart` activation flags | Runtime activation must be explicit and gated. |
| Unreviewed regulatory compliance claims | Must be evidence-backed and externally reviewed. |

## Required change intake checklist

Before editing, record:

1. Task scope and exact files to change.
2. Whether the change touches safe, conditional, or no-touch zones.
3. ADR reference if a conditional zone is touched.
4. Secret-handling impact.
5. Network/egress impact.
6. Tests or gates that will prove the change.
7. Rollback path for deployment or public-surface changes.

## Examples

### Allowed without ADR

- Add a unit test for a validator.
- Add a no-network diagnostic under `scripts/commander/`.
- Update an operations runbook with `VERIFIED` / `UNVERIFIED` evidence labels.

### Requires ADR or explicit exception

- Changing `render.yaml` service target.
- Adding a new public static path under `public/`.
- Changing runtime routing for sensitive data.
- Adding a workflow that can deploy production resources.

### Rejected by default

- Adding a product dashboard to `public/`.
- Adding `/api/*` routes to this repository.
- Calling Modal endpoints from browser JavaScript.
- Claiming SAMA/NCA/PDPL compliance without evidence.

## Review standard

A PR touching conditional zones must include:

- design decision,
- boundary impact,
- tests and command output,
- rollback plan,
- explicit statement that no secrets are exposed,
- evidence labels for readiness claims.
