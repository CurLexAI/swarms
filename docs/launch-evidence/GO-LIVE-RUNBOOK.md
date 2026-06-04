# Go-Live Runbook — Qarar / Bayyinah (sovereign agents + product surfaces)

Status: **REFERENCE RUNBOOK** (planning/coordination only — no production action is
taken by reading or merging this document).
Principle: **verification before activation.** No deploy, merge, external mutation,
or live-control action happens without explicit owner approval and a passing gate.

This is the single end-to-end map of what remains to take the whole system live. It
spans two boundaries that ADR-0001 keeps separate:

- **Track A — Sovereign agent runtime** — lives in **this repo** (`CurLexAI/swarms`):
  Mihwar/Bayyinah on Modal + the Bayyinah PR gate. This runbook can drive Track A.
- **Track B — Product application surfaces** — live in **other repositories**
  (backend API, customer page, engineer dashboard, marketing/site, edge). ADR-0001
  forbids that source here, so this runbook only **specifies** Track B; the work
  must happen in the product repo(s). In the `CurLexAI` org the only active
  non-`swarms` repo visible from this session is `FRONT` (private); no backend /
  customers / dashboard / product-monorepo repo is visible here.

> Authoritative records: `docs/decisions/ADR-0001-swarms-boundary.md` (boundary),
> `ADR-0003-qala-security-architecture.md` (Qala), `ADR-0004-qala-modal-edge-hmac-auth.md`
> (edge↔Modal HMAC), `ADR-0004-canonical-platform-surfaces.md` (product surfaces),
> `ADR-0005-public-llm-gateway.md`, `ADR-0006-fastapi-secondary-ai-gateway.md`,
> `ADR-0007-sovereign-incident-decision-service.md`.
> Live-readiness evidence: `docs/launch-evidence/launch-evidence.json` (verdict `HOLD`).

---

## 0. Current verdict

`HOLD`. Phases 1–3 (Governance, Secrets manifest, Local gates) are `VERIFIED` on
`main`. Everything live (Phases 4–11 of Track A, and all of Track B) is blocked on
owner-provisioned secrets + explicit production approval + live smoke evidence.
Documentation-only evidence may **never** yield `READY`.

---

## Track A — Sovereign agent runtime (this repo)

### A1. Secrets (owner) — Phase 2 precondition
Provision in GitHub Actions / the secret manager (never in repo or chat). Required
set per `docs/launch-evidence/secrets-manifest.json`:
`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`,
`BAYYINAH_API_TOKEN`, `MIHWAR_API_TOKEN` (the two endpoint tokens **must differ**).
Plus, for the constrained dispatcher: `ACTIONS_DISPATCH_PAT` (Actions RW only).

Verify names only (fail-closed), never values:
```bash
python3 scripts/check-secrets-manifest.py --phase modal-deploy     # must PASS
python3 scripts/check-secrets-manifest.py --phase endpoint-smoke   # must PASS
```

### A2. Environment protection (owner)
`Settings → Environments → production`: enable **Required reviewers**, restrict
**Deployment branches** to `main`. (Prevents any unattended production deploy.)

### A3. Phase 4 — Modal deploy (manual, approval-gated)
One of:
- `Actions → modal-deploy → Run workflow` → `confirm_deploy = DEPLOY_MODAL`; or
- `Actions → Runtime Dispatcher → Run` → `target=activate, confirm=ACTIVATE`
  (uses `ACTIONS_DISPATCH_PAT`; both the dispatcher and the activation workflow are
  `production`-gated and re-validate the confirm phrase).
Approve the `production` environment prompt. **No push/schedule path deploys** (audited).

### A4. Phase 5 — Modal CLI smoke (after approved deploy)
```bash
bash scripts/commander/modal-runtime-smoke.sh
```
Confirm: import OK, secret access OK, model available, safe test inference; record
outputs with no sensitive data.

### A5. Phase 6 — Endpoint smoke + token isolation (the decisive gate)
Verify, against the live endpoints:
- Bayyinah and Mihwar each return **HTTP 200** to an authenticated request;
- each endpoint **rejects the other endpoint's token** (cross-token negative test);
- logs expose **no** secrets;
- the only acceptable launch verdict string is `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION`.

### A6. Phase 7 — Bayyinah PR gate is merge-blocking (owner)
Confirm branch protection on `main` **requires** the `agent-review` check, so a
`REQUEST_CHANGES` / unverified verdict blocks merge. (`agent-review.yml` already
exits non-approving when secrets are absent.)

### A7. Phase 8 — Control boundary (live)
Exercise the Aegis MCP gateway / `PolicyService`: allowed command passes, disallowed
blocks, unclassified data blocks, restricted data takes the sovereign-only route,
every decision is audit-logged (Qala hash-chain, ADR-0003).

### A8. Phases 9–11 — pilot → limited live → full live
- **9 Device/connectivity pilot:** low-risk commands only; allowlisted device, kill
  switch, audit trail, no destructive control, manual operator present.
- **10 Limited live:** rate limits, monitoring, rollback, error budget, audit export.
- **11 Full live:** all gates green, no CRITICAL/HIGH, stable endpoint smoke, PR gate
  blocks correctly, control boundary verified, incident path tested (ADR-0007).

---

## Track B — Product surfaces (OTHER repos; specification only)

> Forbidden in `swarms` (boundary gate fails on `backend_fastapi/`, `src/routes/`,
> `public/index.html`, marketing pages). Implement these in the product repo(s).
> Status here is `EXTERNAL / UNVERIFIED` because the source is not in this session.

### B1. Backend API (origin)
- Serves customer + engineer surfaces; deploys to **Render origin** behind
  **Cloudflare edge** (`render-deploy.yml` is the gated origin-deploy pattern to mirror).
- Calls sovereign agents **only** via the **edge↔Modal HMAC** contract (ADR-0004 HMAC);
  Modal stays **backend-only** — never expose `*.modal.run` to any client.
- Request path enforces the Qala input gate + KSA PII redaction before routing
  (ADR-0003), and writes the hash-chained audit trail.
- Optional public LLM gateway / FastAPI secondary AI gateway per ADR-0005 / ADR-0006
  (separate, explicitly-authorized egress — not the sovereign path).

### B2. Frontend — customer page + engineer dashboard
- Likely `CurLexAI/FRONT` (confirm). Build + deploy (e.g. `vercel-deploy.yml` pattern
  for the public surface) with **CSP + SRI** enforced.
- **Customer page:** authenticated entry to the assistant; shows only sanitized output.
- **Engineer dashboard:** operational/control view; must never render Modal endpoints,
  tokens, or raw audit secrets; control actions go through the backend boundary, not
  directly to Modal.
- Canonical surfaces defined in `ADR-0004-canonical-platform-surfaces.md` — align the
  frontend routes/pages to it.

### B3. End-to-end integration test (cross-repo)
`Client → Frontend → Backend (Qala input gate + PII redaction) → router → Modal
(Mihwar→Bayyinah) → Bayyinah validation gate → response`, with the Qala audit
hash-chain intact end to end. Add a synthetic, public-data smoke that exercises this
full path and asserts no secret/PII leakage and no `*.modal.run` reaching the client.

### B4. Compliance & data residency
Do **not** claim SAMA / PDPL / NCA readiness without cited evidence. Confirm egress
residency (Qala Q8 allowlist) holds across the product egress surface too.

---

## Cross-cutting: rollback, kill switch, incident, sign-off

- **Rollback:** Modal → redeploy prior known-good revision (or stop app); backend/edge
  → re-point to previous build; config → revert version-controlled `agents.yaml`.
- **Kill switch:** stop the Modal app (endpoints 5xx → PR gate degrades to non-approving,
  fail-closed); revert a Q8 allowlist entry to fail-close an egress host.
- **Incident path (ADR-0007):** detect → contain (kill switch) → triage severity →
  notify owner → remediate on a branch → re-run gates + endpoint smoke before
  re-activation → record in `launch-evidence.json`. No re-activation with any open
  CRITICAL/HIGH.

### Final sign-off (all must be true for `Full live`)
- [ ] Track A Phases 4–8 each produced a live `VERIFIED` evidence record.
- [ ] `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION` recorded.
- [ ] Bayyinah PR gate confirmed merge-blocking.
- [ ] Track B B1–B3 deployed and end-to-end smoke passed (in product repo CI).
- [ ] No CRITICAL/HIGH blockers open; incident path tested.
- [ ] Owner production approval recorded.

Until every box is checked, the program verdict stays **`HOLD`**.
