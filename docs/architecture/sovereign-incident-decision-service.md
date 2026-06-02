# Sovereign Incident Decision Service Architecture

## Purpose

The Sovereign Incident Decision Service is a domain decision engine for
security incident assessment. It turns normalized evidence and policy context
into auditable decision records and approval-gated action intents.

It is not a remediation runtime. It does not directly isolate devices, disable
accounts, change firewall rules, mutate EDR policy, or open SOAR cases in v0.

## Repository boundary

In `CurLexAI/swarms`, this architecture is a specification only. The repository
may host future domain-contract tests or fake-port prototypes, but it must not
host the production incident runtime service.

Allowed in `CurLexAI/swarms`:

- ADRs and architecture specifications,
- domain model sketches,
- fake adapters for contract tests,
- append-only audit semantics,
- Qarar-Sec reviewer/analyzer profile work that remains transport agnostic.

Not allowed in `CurLexAI/swarms`:

- REST or GraphQL incident service surfaces,
- queue consumers or schedulers,
- database migrations,
- SIEM, SOAR, EDR, IAM, NAC, MDM, firewall, or telecom integrations,
- cloud AI analysis adapters,
- autonomous enforcement.

## Hexagonal architecture

```text
                 +--------------------------------+
                 |  Incident Decision Domain      |
                 |--------------------------------|
                 |  Evidence normalization        |
                 |  Policy evaluation             |
                 |  Risk scoring                  |
                 |  Decision records              |
                 |  Approval-gated action intents |
                 +--------------------------------+
                         ^                ^
                         | Ports          | Ports
        +----------------+                +----------------+
        |                                                  |
+-------------------+                         +------------------------+
| Evidence Ports    |                         | Output Ports           |
|-------------------|                         |------------------------|
| IncidentReader    |                         | DecisionRecorder       |
| AssetContext      |                         | AuditLedger            |
| IdentityContext   |                         | ApprovalRequestWriter  |
| DevicePosture     |                         | NotificationDraftSink  |
+-------------------+                         +------------------------+
        ^                                                  ^
        | fake adapters in v0                              | fake adapters in v0
        | production adapters later                        | production adapters later
```

The domain owns decisions. Adapters only translate data into or out of domain
ports. Dependency injection must provide all ports so tests can run with fake
adapters and without network, secrets, or external systems.

## v0 scope

The first executable version must be domain-only and read-only:

1. Accept a normalized incident evidence object.
2. Validate classification, tenant, actor, timestamps, and evidence source.
3. Evaluate local deterministic policy rules.
4. Produce a decision record.
5. Produce zero or more action intents.
6. Mark high-impact action intents as `approval_required`.
7. Append an audit record through an injected audit port.
8. Use fake adapters in tests.

No v0 path may call a live SIEM, SOAR, EDR, IAM, NAC, MDM, firewall, telecom,
cloud AI, or external notification provider.

## Core domain concepts

| Concept | Responsibility |
|---|---|
| `IncidentEvidence` | Normalized read-only incident facts, references, source metadata, and classification. |
| `IncidentContext` | Tenant, actor, asset, device posture, identity posture, and policy context. |
| `DecisionPolicy` | Deterministic rule set that maps evidence and context to a decision. |
| `DecisionRecord` | Immutable decision output with rationale, confidence, references, and audit metadata. |
| `ActionIntent` | Proposed action, never direct execution. High-impact intents require approval. |
| `ApprovalRequirement` | Human or policy gate required before any destructive or high-impact action. |
| `AuditEntry` | Append-only record containing decision metadata and evidence hashes, not raw sensitive payloads by default. |

## Port boundaries

### Input ports

- `IncidentEvidenceReader`: retrieves or receives normalized incident evidence.
- `AssetContextProvider`: provides asset criticality and ownership context.
- `IdentityContextProvider`: provides identity risk and privilege context.
- `DevicePostureProvider`: provides posture evidence such as attestation status,
  compliance state, and management status.
- `PolicyProvider`: provides local deterministic decision policy.

### Output ports

- `DecisionRecorder`: persists immutable decision records.
- `AuditLedger`: appends hash-linked audit metadata.
- `ApprovalRequestWriter`: writes approval requests for high-impact intents.
- `NotificationDraftSink`: creates drafts only; it does not send external
  notifications in v0.

### Deferred adapters

The following adapters are explicitly deferred until a production service
repository, security review, and operational ownership exist:

- `SiemIncidentAdapter`,
- `SoarCaseAdapter`,
- `EdrActionAdapter`,
- `IamPrivilegeAdapter`,
- `NacQuarantineAdapter`,
- `MdmDeviceActionAdapter`,
- `CloudAIAnalysisAdapter`.

If `CloudAIAnalysisAdapter` is ever introduced, it must be disabled by default
and accept only minimized, redacted, explicitly approved evidence.

## Decision lifecycle

```text
RECEIVED
  -> VALIDATED
  -> POLICY_EVALUATED
  -> DECISION_RECORDED
  -> INTENTS_CREATED
  -> APPROVAL_REQUESTED (when needed)
  -> CLOSED_WITHOUT_MUTATION (v0 default)
```

There is no `EXECUTED` state in v0 because direct enforcement is out of scope.
Future execution states require a separate ADR and production runtime review.

## Safety invariants

- Raw secrets, tokens, credentials, private keys, and live endpoint URLs must
  never be stored in decision records.
- Raw sensitive evidence must be minimized; audit records should store stable
  references and hashes unless policy explicitly permits more detail.
- Every decision must include tenant, actor, policy version, evidence reference,
  classification, and timestamp.
- Every high-impact action intent must include an approval requirement.
- A missing policy, missing classification, missing tenant, or ambiguous impact
  level must fail closed.
- Tests must prove fake adapters are used by default.

## Suggested future PR sequence

1. `feat(incident): add read-only incident decision domain model`
   - domain entities only,
   - fake ports only,
   - unit tests for fail-closed validation and approval-required intents.
2. `feat(incident): add append-only decision audit contract`
   - hash-linked audit metadata,
   - no raw sensitive payload by default.
3. `feat(incident): add Qarar-Sec reviewer profile`
   - analyzer/reviewer role only,
   - no external transport activation.
4. Separate product/control-plane repository PRs for runtime ingress,
   persistence, mTLS, and production adapters.

## Non-goals

- Building a new incident runtime inside `CurLexAI/swarms`.
- Replacing Qal'a audit gates.
- Bypassing Mihwar/Bayyinah review workflows.
- Claiming regulatory compliance from documentation alone.
- Activating cloud AI, SIEM, SOAR, EDR, IAM, NAC, MDM, firewall, or telecom
  integrations.
