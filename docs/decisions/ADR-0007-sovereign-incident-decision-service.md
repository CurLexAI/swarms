# ADR-0007 — Sovereign Incident Decision Service as External Decision Layer

- **Status:** Decided — Design GO; implementation in `CurLexAI/swarms` WAIT; runtime service inside `CurLexAI/swarms` NO-GO.
- **Decision date:** 2026-06-02
- **Decision recorded:** 2026-06-02
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none
- **Relates to:** ADR-0001 (swarms boundary), ADR-0003 (Qal'a security architecture), ADR-0004 (canonical platform surfaces), ADR-0006 (secondary AI execution adapter)
- **Hot-surface classification:** YES — a full incident decision service would eventually touch security evidence, policy decisions, approvals, queues, databases, and external security tooling.

## Context

`CurLexAI/swarms` is currently an agent operations, governance, validation,
and review-automation repository. It is not the recovered LexPrim product
monorepo and it is not the appropriate home for a new always-on incident
runtime with REST ingress, queues, databases, SIEM adapters, SOAR adapters,
EDR adapters, or network enforcement integrations.

The proposed Sovereign Incident Decision Service is architecturally valuable
because it separates decision-making from direct enforcement. That separation
is the correct posture for a sovereign control plane: the service can produce
traceable recommendations, policy outcomes, and approval requests while
leaving destructive or high-impact execution behind explicit human and policy
gates.

The service must therefore start as a documented domain boundary and not as a
new operational runtime inside this repository.

## Decision

### 1. Design direction is accepted

The Sovereign Incident Decision Service is accepted as a strategic design
concept.

It is a **decision layer**, not an isolation, blocking, or remediation engine.
It may classify incidents, evaluate evidence, recommend actions, and produce
approval-gated decision records. It must not directly disable accounts,
quarantine devices, alter firewall rules, mutate EDR policy, open SOAR cases,
or call external security systems in its initial form.

### 2. Runtime implementation inside `CurLexAI/swarms` is rejected

`CurLexAI/swarms` must not host the full runtime implementation of this
service. In this repository, the allowed scope is limited to:

- this ADR,
- a domain specification,
- future fake-port prototypes,
- future domain-contract tests,
- a future Qarar-Sec reviewer/analyzer agent profile if it remains transport
  agnostic and does not activate external systems.

The following are explicitly out of scope for `CurLexAI/swarms` under this ADR:

- new public or internal REST service surfaces,
- new message queues,
- new database migrations or Postgres schema,
- SIEM adapters,
- SOAR adapters,
- EDR, IAM, NAC, MDM, firewall, or mTLS-control integrations,
- cloud AI evidence analysis,
- autonomous remediation or isolation actions.

### 3. Product/control-plane implementation belongs elsewhere

The future production service should live in the LexPrim/Qarar product or
Mihwar service repository, after the repository gates and product runtime
boundaries are established there.

That target repository will be responsible for runtime concerns such as:

- REST or message-driven ingress,
- Postgres or an equivalent durable store,
- append-only audit ledger persistence,
- mTLS service identity,
- policy-engine integration,
- SIEM/SOAR/IAM/NAC/EDR/MDM adapter hardening,
- deployment topology,
- operational runbooks and SLOs.

### 4. Version 0 must be read-only and local-first

The first implementation phase, wherever it is later hosted, must be:

- read-only,
- local-first,
- dependency-injected,
- based on Ports and Adapters,
- backed by fake adapters only,
- append-only for audit records,
- approval-gated for any high-impact action,
- free of SOAR mutations,
- free of cloud AI calls.

A `CloudAIAnalysisAdapter` must not be part of the early executable design. If
introduced later, it must be disabled by default and restricted to
redacted/minimized evidence under an explicit data-classification and egress
approval policy.

## Naming

Use distinct names for the service, agent, and domain package:

| Concern | Name |
|---|---|
| Service | `Sovereign Incident Decision Service` |
| Agent/reviewer | `Qarar-Sec` |
| Domain package | `incident_decision` |

`Qarar-Sec` is a reviewer/analyzer role. The Sovereign Incident Decision
Service is the decision, policy, and evidence service.

## Rejected alternatives

### Build the full service now in `CurLexAI/swarms`

Rejected. This would conflict with ADR-0001 by turning an agent-operations
repository into an incident runtime service repository and would invite
forbidden runtime surfaces and activation behavior.

### Add SIEM/SOAR/EDR adapters immediately

Rejected. Those adapters are high-impact integration points. They require
separate threat modeling, mTLS identity, least-privilege credentials,
redaction, replay protection, approval gates, and operational ownership.

### Add cloud AI analysis as a first-class adapter in v0

Rejected. Incident evidence may contain sensitive operational, security, user,
or device data. Cloud analysis requires a later explicit egress policy,
redaction/minimization controls, audit evidence, and human approval.

### Put all logic inside a Qarar-Sec agent

Rejected. Agent analysis is useful, but the decision service needs stable domain
contracts, policy evaluation, audit records, and approval semantics that do not
depend on one agent implementation.

## Consequences

- `CurLexAI/swarms` may add documentation and future domain-only fake-port
  prototypes for `incident_decision`.
- `CurLexAI/swarms` must not add the full runtime service or security-tooling
  adapters under this ADR.
- Future implementation work must be split into small PRs:
  1. domain contracts and fake ports,
  2. append-only audit record model,
  3. policy decision outcomes,
  4. approval-gated action intents,
  5. production adapters only after a separate runtime repository and security
     gate review exist.
- Any future PR that adds executable code must prove that destructive actions
  are represented as approval-required intents, not direct mutations.

## Verification

This ADR is documentation-only. It authorizes no runtime, deployment, external
adapter, cloud AI call, database, queue, or public surface.

Evidence labels:

- `VERIFIED` — ADR-0001 exists and defines the `swarms` repository boundary.
- `VERIFIED` — this ADR adds no executable runtime code.
- `INFERRED` — the production implementation will need a separate
  product/control-plane repository because the listed runtime dependencies are
  outside the current `swarms` operations boundary.
