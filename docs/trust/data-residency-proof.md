# Data Residency Proof

## Purpose
This document defines the canonical data-flow map, residency evidence set, and control-state tracking for user data handled by the CurLexAI swarms operating stack.

## Review Metadata
- Last reviewed (UTC): 2026-05-08
- Evidence scope: Render + Modal official documentation and legal pages.
- Public claim gate: **No public residency claim is allowed unless internal approval record is `VERIFIED`.**

## Canonical Data-Flow Map

```text
Browser
  ↓ (HTTPS request metadata + user payload)
Backend
  ↓ (provider API call with scoped payload)
Model Runtime
  ↓ (response payload + operational metadata)
Storage/Logs
```

## Official Evidence Register (Render + Modal)

| Provider | Evidence topic | Official source | Key statement used internally | Evidence status | Reviewed on (UTC) |
|---|---|---|---|---|---|
| Render | Runtime regions | https://render.com/docs/regions | Render service/datastore regions listed as Oregon, Ohio, Virginia, Frankfurt, Singapore. | VERIFIED | 2026-05-08 |
| Render | Static CDN behavior | https://render.com/docs/regions and https://render.com/docs/static-sites | Static sites are global-CDN-backed and do not expose a user-selectable region. | VERIFIED | 2026-05-08 |
| Render | Storage backup retention | https://render.com/docs/postgresql-backups | Logical Postgres exports are retained for seven days after creation. | VERIFIED | 2026-05-08 |
| Render | Subprocessors reference point | https://render.com/dpa | DPA points to `https://render.com/trust` as the authorized subprocessor list location. | VERIFIED (reference path), UNVERIFIED (list contents) | 2026-05-08 |
| Modal | Runtime regions + control-plane routing | https://modal.com/docs/guide/region-selection | Function/Sandbox region can be specified; I/O still traverses control plane in `us-east-1`. | VERIFIED | 2026-05-08 |
| Modal | Subprocessors reference point | https://modal.com/legal/dpa | DPA Schedule 3 points to `https://trust.modal.com/subprocessors`. | VERIFIED (reference path), UNVERIFIED (list contents) | 2026-05-08 |
| Modal | Storage/volume residency detail | https://modal.com/docs/guide/volumes | Public page reviewed; no explicit regional storage-at-rest matrix extracted in this run. | UNVERIFIED | 2026-05-08 |

## Internal Environment Region Register

| Service surface | Concrete service/provider | Configured region | Evidence source | Status | Owner |
|---|---|---|---|---|---|
| backend runtime | Render Web Service | UNVERIFIED (dashboard value required) | Runtime options documented at Render regions doc | UNVERIFIED | Platform Engineering |
| logs / audit sink | Render logs + optional external sink | UNVERIFIED (actual sink + region not captured) | Repo docs + platform docs; no live dashboard export attached | UNVERIFIED | Security Engineering |
| model runtime | Modal Function/Sandbox | UNVERIFIED (exact configured runtime region not captured from deployment config) | Modal region selection doc confirms mechanism, not this repo's active value | UNVERIFIED | ML Platform |
| CDN / edge delivery | Render Static Site CDN | Global edge POPs (vendor-managed), origin region not directly selectable for static surface | Render regions/static-sites docs | PARTIALLY VERIFIED | Platform Engineering |

## Data Channel Control Record

| Channel | Status | Reason |
|---|---|---|
| CDN / analytics | UNVERIFIED | CDN behavior is documented, but no repository-bound analytics vendor inventory with region map was found in this pass. |
| Error tracking | UNVERIFIED | No canonical error-tracking vendor + region evidence artifact is currently attached in `docs/trust/`. |
| Model hops | PARTIALLY VERIFIED | Modal control-plane path via `us-east-1` is documented; active deployment region(s) and full subprocessor chain remain unverified. |
| Logging | UNVERIFIED | Logging channels are listed conceptually, but no exported runtime configuration proves exact storage/processing region. |

## Security/Compliance Approval Record (Public Claim Gate)

- Record ID: CCR-DR-2026-05-08-01
- Required approver role: Internal Security or Compliance Officer
- Approval timestamp (UTC): UNVERIFIED
- Approval evidence artifact: UNVERIFIED (no signed memo/issue comment attached)
- Gate result: **BLOCKED** for any new public residency/compliance claim.

## Quarterly Follow-up Ticket

- Ticket ID: GOV-DR-EVIDENCE-REVALIDATION-Q3-2026
- Cadence: Quarterly
- Next due date (UTC): 2026-08-01
- Scope:
  1. Re-check Render `regions`, `postgresql-backups`, and DPA subprocessor pointer.
  2. Re-check Modal `region-selection`, DPA subprocessor pointer, and trust center list availability.
  3. Export live deployment regions from platform dashboards and reconcile with this register.
  4. Re-run control record statuses and update approval gate.
- Current status: OPEN

## Decision Rule
Without the approval record and live-environment region exports, external-facing residency statements remain `UNVERIFIED` and must not be promoted as compliance facts.
