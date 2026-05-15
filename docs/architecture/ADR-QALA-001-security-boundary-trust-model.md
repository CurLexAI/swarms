# ADR-QALA-001: QAL'A Security Boundary and Trust Model

- Status: Proposed
- Date: 2026-05-15
- Decision Owner: CurLexAI Security Engineering
- Scope: CurLexAI/swarms (agent operations repository)
- Related: ADR-0001, ADR-0002 (repo boundary and identity)

## Context

CurLexAI/swarms operates as an agent operations and validation layer. It contains agent orchestration, validation gates, and runtime glue, but it is not the product application runtime. The QAL'A sovereign cybersecurity layer requires explicit boundaries and trust contracts before any hot-surface security implementation.

This ADR establishes the first security foundation for QAL'A and constrains subsequent implementation phases.

## Decision

### 1) Security boundaries for CurLexAI/swarms

QAL'A boundary model for this repository:

1. **Repository boundary (operations-only):**
   - In-scope: `.agents/`, `src/services/`, `scripts/commander/`, `docs/`, tests, and governance assets.
   - Out-of-scope: product runtime/API surface, customer-facing application logic, production data processing paths.

2. **Execution boundary:**
   - GitHub Actions executes policy checks, review orchestration, and boundary gates.
   - Modal endpoints execute model-facing workloads.
   - Node/Python service adapters mediate internal agent execution requests.

3. **Secrets boundary:**
   - Secret values must remain externalized (CI secret stores/runtime secret managers).
   - Repository content and logs must not include raw secret values.

4. **Evidence boundary:**
   - Security claims are accepted only with direct execution evidence from tests, gates, or runtime probes.

### 2) Trust model between components

Trust levels are explicit and minimal:

- **T0 (Untrusted input):** external caller payloads, PR diffs, issue/comment text, model-generated content.
- **T1 (Conditionally trusted control plane):** GitHub workflow context and repository metadata, subject to trigger and permission constraints.
- **T2 (Conditionally trusted runtime):** Modal and agent runtime responses, accepted only after validation and policy checks.
- **T3 (Trusted governance artifacts):** accepted ADRs, policy files, validation scripts, and signed/approved repository changes.

Required trust transitions:

1. External input (T0) → validated schema and policy checks before any agent/runtime dispatch.
2. Workflow trigger context (T1) → bounded authorization checks before invoking runtime endpoints.
3. Runtime output (T2) → output validation and audit capture before downstream use.

No direct trust jump from T0 to T2/T3 is allowed.

### 3) Allowed first implementation layer

The only implementation layer authorized immediately after this ADR is:

- **Shared trace + audit schema (Phase 2B)**
  - Standard event envelope for security-relevant actions.
  - Correlation IDs across workflow, adapter, and runtime boundaries.
  - Minimal required fields for actor, action, boundary, policy decision, and outcome.
  - Redaction-aware payload handling.

### 4) Deferred layers requiring separate ADRs

The following layers are explicitly deferred and blocked from implementation until dedicated ADR approval:

1. **Modal-edge HMAC service authentication** (hot surface)
2. **Fail-closed egress/network guard** (hot surface)
3. **Sarab deception/honeypot layer** (hot surface)

These are high-impact boundary changes and require explicit architecture, threat model, rollback, and test strategy in their own ADRs.

### 5) Hot-surface changes list

Hot-surface changes are any modifications that alter trust boundaries or execution control over:

- `.agents/modal_app.py`
- `.agents/pr_review.py`
- `.github/workflows/*`
- Agent invocation/auth relay paths
- Network/egress decision points
- Identity and signing contracts between GitHub, Modal, and agent adapters

Any PR touching hot-surface files must include:

- explicit threat impact statement,
- rollback steps,
- fail-closed behavior statement,
- targeted tests proving intended behavior and denial behavior.

### 6) Review gates per phase

Required review gates:

1. **ADR phase gates (docs-only phases):**
   - ADR completeness review
   - boundary consistency check against existing ADR-0001/ADR-0002
   - no runtime code modification

2. **Code phase gates (implementation phases):**
   - repository boundary gates (`scripts/commander/*`)
   - targeted tests for changed trust boundary
   - regression checks for denial path (fail-closed where applicable)
   - evidence capture in PR body (commands + outputs)

3. **Hot-surface phase gates:**
   - mandatory separate ADR pre-approved
   - conflict scan for overlapping PRs on same trust surface
   - sequenced rollout and rollback rehearsal plan

### 7) Rollback strategy

QAL'A changes must support fast rollback per phase:

1. **ADR-only rollback:** revert documentation PR; no runtime side effects.
2. **Code rollback:** single-PR revert restoring prior trust path.
3. **Hot-surface rollback:**
   - immediate fallback to previous authenticated path,
   - disable new enforcement toggle if present,
   - preserve audit evidence of rollback trigger and timestamp,
   - rerun boundary and regression gates before re-attempt.

Rollback is mandatory if any of the following occurs:

- trust contract mismatch,
- false deny on critical control-plane path without mitigation,
- inability to prove fail-closed behavior where required,
- security regression in boundary gates.

## Consequences

1. Phase sequencing is now constrained: ADR-first, then minimal implementation layer, then deferred hot-surface ADRs.
2. No team member or agent may implement HMAC edge auth, Sarab, or egress blocking under QAL'A without dedicated ADR approval.
3. QAL'A delivery remains reviewable through small, isolated PRs with explicit trust-boundary evidence.

## Non-goals

This ADR does not:

- activate agents,
- modify runtime code,
- deploy Modal changes,
- alter GitHub workflows,
- claim legal certification/compliance status.

## Approval requirements for next step

Before starting Phase 2B (shared trace + audit schema), reviewers must confirm:

1. This ADR is accepted.
2. Scope remains limited to non-hot-surface implementation.
3. PR decomposition sequence remains intact.
