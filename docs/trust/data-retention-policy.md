# Data Retention and Deletion Policy

## Purpose
This policy defines retention periods, deletion mechanisms, and legal-hold handling for data processed by CurLexAI swarms operations.

## Retention Schedule

| Data Category | Examples | Default Retention | Deletion Trigger | Status |
|---|---|---|---|---|
| Application request records | API request metadata, task IDs, status | 90 days | Age-based lifecycle job | CHANGED BUT NOT VERIFIED |
| Audit/security logs | Access records, security events, policy violations | 365 days | Immutable-log expiry policy | CHANGED BUT NOT VERIFIED |
| Error/diagnostic logs | Stack traces, runtime error payloads | 30 days | Log sink TTL rule | CHANGED BUT NOT VERIFIED |
| Model interaction artifacts | Prompt/response traces when enabled | 30 days | Scheduled purge job + scoped delete API | CHANGED BUT NOT VERIFIED |
| Backup snapshots | Encrypted operational backups | 35 days rolling | Backup lifecycle expiration | CHANGED BUT NOT VERIFIED |

> Note: Any retention value above is policy baseline and must be validated against actual platform configuration before external assurance statements.

## Deletion Mechanism
1. **Scheduled deletion**: automated lifecycle rules purge records at retention boundary.
2. **On-demand deletion**: authenticated deletion request removes tenant/user scoped records where technically supported.
3. **Propagation**: deletion request is propagated to integrated processors/subprocessors according to contractual controls.
4. **Audit trail**: deletion requests and outcomes are logged with timestamp, actor, scope, and result.

If a subsystem cannot execute deletion automatically, its status must remain `UNVERIFIED` until compensating control is documented.

## Legal Hold
- Legal hold overrides standard retention deletion for scoped records under investigation, litigation, or regulatory requirement.
- Hold activation requirements:
  - authorized requester identity;
  - explicit scope (tenant, dataset, time range);
  - start date and review date.
- While hold is active, automated purge for scoped data is suspended.
- Hold release requires documented approval and release timestamp; normal retention timers then resume per policy.

## Marketing Claim Editing Rule (Sovereignty Claims)
Any sovereignty/data-residency claim in marketing or public content is allowed only when evidence is:
1. **Current** (not stale relative to deployed architecture);
2. **Internally signed** (security/compliance owner sign-off);
3. **Traceable** to concrete system evidence (region map, providers, subprocessors, retention controls).

If one condition is missing, the claim must not be published and must be marked `UNVERIFIED` internally.
