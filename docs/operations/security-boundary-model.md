# Security & Boundary Model

Date: 2026-06-30
Scope: `CurLexAI/swarms` as the CurLexAI agent operations and control-plane repository.

## Goal

Keep the repository as a sovereign control plane for agents and validation while
preventing accidental public surfaces, model-boundary bypasses, and unsupported
runtime-readiness claims.

## Evidence rule

Every material security claim must use exactly one evidence label:

- `VERIFIED` — supported by repository content, command output, CI artifact, or live smoke evidence.
- `INFERRED` — reasonable from available evidence but not directly proven.
- `UNVERIFIED` — not checked, blocked by missing secrets, blocked by runtime access, or outside repository scope.

## Boundary layers

### 1. Static boundaries

These paths define repository identity or deployment posture and require ADR
review before material changes:

| Boundary | Rule |
| --- | --- |
| `public/` | Only ADR-approved static operator surfaces are allowed. |
| `render.yaml` | Deployment blueprint changes require ADR or explicit operator service evidence. |
| `.github/workflows/**` | CI/CD changes require fail-closed behavior and minimum permissions. |
| `src/runtime-policy.ts` | Runtime policy changes require policy tests and reviewer approval. |
| `src/policy/**` | Sovereign policy logic requires tests and no downgrade of data classification. |
| `docs/decisions/**` | ADRs are append-only decision records; changes must preserve traceability. |
| `docker-compose*.yml` | Network/service topology changes require threat impact review. |

### 2. Dynamic boundaries

#### Runtime policy

Runtime policy decides what an agent can do, what tools it may call, which data
classifications are allowed, and whether a request may leave the local control
plane.

Required properties:

- fail closed on unknown classification,
- never route `CONFIDENTIAL` or `RESTRICTED` data to non-sovereign providers,
- keep cloud fallback disabled unless explicit egress approval and redaction
  evidence exist,
- emit evidence that can be audited.

#### Validators

Validators guard inputs and outputs before any agent or runtime path is trusted.
They must reject malformed input, policy violations, prompt-injection markers,
secret-like values, and unauthorized tool requests.

#### Routers

Routers select models and providers. They must respect data classification,
provider allowlists, local-first posture, and token/endpoint isolation.

### 3. CI security gates

| Gate | Purpose |
| --- | --- |
| ADR boundary gate | Blocks forbidden repository/product-surface drift. |
| Modal boundary gate | Prevents Modal endpoint exposure to public/client surfaces. |
| Public surface gate | Limits `public/` to approved static surfaces. |
| SRI gate | Ensures external scripts use integrity and crossorigin. |
| Runtime policy tests | Prove fail-closed classification and routing behavior. |
| Agent presence gate | Confirms configured agents are visible and bounded. |
| Orchestrator workflow | Runs verification first and permits activation only with explicit confirmation. |

### 4. Deployment boundaries

Deployment is allowed only when all applicable statements remain true:

1. No secret values are committed or printed.
2. Modal endpoints remain backend-only.
3. Public Render service exposes static trust content and `/healthz` only.
4. Activation requires explicit confirmation and protected runtime secrets.
5. CI artifacts distinguish `VERIFIED`, `UNVERIFIED`, and `BLOCKED` outcomes.

## Agent boundary map

| Agent / role | Allowed | Blocked |
| --- | --- | --- |
| Mihwar | Architecture, generation, task decomposition through controlled runtime. | Direct browser exposure, public endpoint calls, unreviewed production activation. |
| Bayyinah | Review, validation, security checks, negative-path evidence. | Silent approval, shared token assumptions, bypassing CI gates. |
| Qarar Router | Policy-based routing and local-first model selection. | Size-only routing, cloud egress for sensitive data, unknown provider fallback. |
| Recovery supervisor | Inspect failures, propose patches, request reviews. | Add secrets, deploy production, merge PRs, disable gates. |

## Public surface boundary

`SR.BSM` is restricted to:

- `GET /` mapped to the static trust surface,
- `GET /healthz` returning non-sensitive liveness,
- static assets under `public/trust/**`,
- no forms,
- no customer data,
- no agent execution,
- no private endpoint disclosure.

## Runtime-readiness boundary

A repository merge does not prove runtime readiness. Runtime readiness remains
`UNVERIFIED` until CI artifacts show:

1. repository gates passed,
2. Modal/Render activation completed if requested,
3. Bayyinah and Mihwar endpoint smoke passed,
4. cross-token negative checks returned `401` or `403`,
5. frontend and backend health checks passed,
6. no critical/high findings remain unresolved.
