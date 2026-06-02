# Launch Governance — Qarar / Bayyinah Activation Ladder

Status: **ACTIVE GOVERNANCE RECORD**
Scope: `CurLexAI/swarms` (agent operations and validation layer — see ADR-0001).
Production principle: **verification before activation.** No deployment, merge,
external mutation, or live control action occurs without explicit owner approval.

This document is the Phase 1 governance gate for the 11-step launch ladder. It is
normative: a phase may not be entered until the controls below are satisfied for it.

---

## 1. Launch scope

| In scope | Out of scope |
|---|---|
| Sovereign coding agents (Mihwar, Bayyinah) invoked via Modal vLLM endpoints | LexPrim/Qarar product source (ADR-0001 forbidden paths) |
| Bayyinah PR review gate on this repository | Public REST/GraphQL surfaces, marketing pages |
| Modal runtime deploy + endpoint smoke for the two agents | Any auto-deploy from `push` without approval |
| Local validation gates (`npm run check`, commander gates, pytest) | Customer/legal data movement off the sovereign path |

The ladder activates **agent runtime only**. It does not authorize any product
launch, data ingestion change, or regulatory-compliance claim.

## 2. Data classification rules

| Class | Examples | Allowed egress | Rule |
|---|---|---|---|
| **PUBLIC** | Synthetic code snippets, public model ids | HF inference router (`router.huggingface.co`), `huggingface.co` | The HF public smoke test (`scripts/hf_public_coding_smoke.py`) may send PUBLIC only. |
| **INTERNAL** | PR diffs, repo source under review | Sovereign Modal endpoints only (`*.modal.run`) | Routed to Mihwar/Bayyinah over authenticated Modal calls; never to third-party AI. |
| **RESTRICTED** | Legal corpora, customer data, secrets | **None** — sovereign path only | Must never leave the sovereign route. Egress attempts fail closed (Q8 gate). |

Enforcement: the Qal'a egress residency gate (Q8,
`scripts/commander/qala-egress-residency-gate.sh` +
`.agents/policies/qala-egress-residency.md`) scans source for any host outside the
documented allowlist and fails closed.

## 3. Owner approvals

| Action | Required approver | Mechanism |
|---|---|---|
| Merge any PR | Repo owner / human reviewer | GitHub review; no merge with unresolved CRITICAL/HIGH |
| Modal deploy (Phases 4–5) | Repo owner | `workflow_dispatch` + typed confirm + `production` environment reviewers |
| Render/edge deploy | Repo owner | `workflow_dispatch` + typed confirm + `production` environment |
| Limited/Full live (Phases 10–11) | Repo owner (explicit) | Documented sign-off recorded in `LAUNCH-READINESS.md` |
| Secret rotation / billing | Repo owner (explicit) | Out of band; never automated by an agent |

No agent (including Claude/Codex automation) may self-approve any of the above.

## 4. Explicit no-auto-deploy rule

- Production deploy paths MUST be `workflow_dispatch` + typed confirmation +
  protected `production` environment. Verified for `modal-deploy.yml`,
  `render-deploy.yml`, and the deploy job of `modal-runtime-auto-activation.yml`.
- A `push` or `schedule` trigger MUST NOT reach a deploy step. Where such triggers
  exist (`modal-runtime-auto-activation.yml`), they are restricted to **smoke-only**
  jobs guarded by `if: github.event_name == 'push' || 'schedule'` and never set
  `deploy_modal=true`. The deploy job is gated on
  `workflow_dispatch && inputs.confirm == 'ACTIVATE'`.
- Any change that would let `push`/`schedule` deploy is a CRITICAL blocker.

## 5. Rollback plan

| Layer | Rollback action |
|---|---|
| Modal runtime | Re-deploy the previous known-good revision via `modal deploy` of the prior commit; or disable the endpoint (Modal app stop). |
| PR change | `git revert` the offending commit; protected branch prevents force-push. |
| Edge/origin | Re-point Render/Cloudflare to the previous build; deploy hooks are manual. |
| Config | `agents.yaml` / `registry.yaml` are version-controlled; revert restores prior topology. |

Rollback never requires secret rotation. Target rollback time: one deploy cycle.

## 6. Kill switch

- **Runtime:** stop the Modal app (endpoints return 5xx; PR gate degrades to
  `UNVERIFIED` and does not approve) — fail-closed by design.
- **PR gate:** Bayyinah review with missing secrets exits non-approving
  (`UNVERIFIED`), so an unhealthy runtime cannot rubber-stamp merges.
- **Egress:** revert an allowlist entry to make the Q8 gate fail closed on the
  corresponding host, blocking its source from passing CI.
- Kill-switch invocation is logged (audit trail, §8).

## 7. Incident path

1. Detect (CI failure, endpoint smoke red, audit anomaly, or owner report).
2. Contain — invoke the relevant kill switch (§6).
3. Triage severity: CRITICAL / HIGH / MEDIUM / LOW.
4. Notify the repo owner (`moteb4092@gmail.com`).
5. Remediate on a branch; re-run local gates + endpoint smoke before re-activation.
6. Record the incident and resolution in `docs/launch-evidence/launch-evidence.json`.
7. No re-activation while any CRITICAL/HIGH remains unresolved.

## 8. Audit & evidence

- Every control-plane decision is audit-logged (`src/services/AuditService`,
  `qala-audit-integrity-gate.sh` verifies chain integrity).
- Every material launch claim carries an evidence label: `VERIFIED`, `INFERRED`,
  `UNVERIFIED`, `SKIPPED_UNVERIFIED`, `NOT_APPLICABLE`.
- Documentation-only evidence may never produce a `READY` verdict.

---

_Authoritative boundary: `docs/decisions/ADR-0001-swarms-boundary.md`._
_Secrets posture: `docs/secrets-policy.md` and `docs/launch-evidence/secrets-manifest.md`._
