# Launch Readiness — Qarar / Bayyinah Activation Ladder

**Final verdict: `HOLD`**

Phases 1–3 are complete and verified in the local launch-evidence branch after
PR #336 was merged into repository history. Phases 4–11 remain blocked pending
merge of the endpoint-token isolation hardening, owner-provisioned secrets, and
explicit production approval. No live runtime evidence exists, so `READY` is not
permissible (documentation-only evidence may never yield `READY`).

- Base: local `work` branch @ `e33c28b0bc0c124114ddf9fb7f96497f5e7aa179`
- Principle: **verification before activation** — no deploy/merge/mutation/live
  control without explicit approval.
- Machine-readable evidence: `docs/launch-evidence/launch-evidence.json`
- Governance: `docs/launch-evidence/LAUNCH-GOVERNANCE.md`
- Secrets: `docs/launch-evidence/secrets-manifest.md` (+ `.json`, validator)

---

## Discovery (template vs. this repo)

This repo is the **agent operations & validation layer** (ADR-0001), not the product
monorepo. Several template-referenced paths do not exist here and are
`NOT_APPLICABLE`: `src/server.js`, `src/app.js`, `data/agents/index.json`,
`data/agents/*.yaml`, `backend/app/services/tree_builder.py` (forbidden zone; the
"known indentation blocker" does not exist here), and a `deploy:evidence:validate`
npm script. Canonical assets that **do** exist: `package.json` (`npm run check`),
`.agents/` (`validate.py`, `modal_app.py`, `config/agents.yaml`),
`agents/registry.yaml` (legacy fallback), `scripts/commander/*` gates, and the
deploy/smoke workflows.

## Phase ladder status

| # | Phase | Status | Evidence |
|---|---|---|---|
| 1 | Governance | ✅ VERIFIED | `LAUNCH-GOVERNANCE.md` authored; ADR-0001 + Q8 policy present |
| 2 | Secrets | ✅ VERIFIED | manifest + validator; `--all` exit=1 fail-closed (6 required UNSET, names only) |
| 3 | Local gates | ✅ VERIFIED | `npm run check`/`test`/`build` exit 0; `validate.py`/`py_compile` exit 0; commander gates PASS after **#336** landed in repository history |
| 4 | Modal deploy | ⛔ BLOCKED | prepared command below; needs `MODAL_TOKEN_*` + approval |
| 5 | Modal CLI smoke | ⛔ BLOCKED | depends on Phase 4 |
| 6 | Endpoint smoke | ⛔ BLOCKED | needs `BAYYINAH_ENDPOINT`/`MIHWAR_ENDPOINT` plus `BAYYINAH_API_TOKEN`/`MIHWAR_API_TOKEN` live and cross-token negative smoke passing |
| 6 | Endpoint smoke | ⛔ BLOCKED | needs live `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, `BAYYINAH_API_TOKEN`, `MIHWAR_API_TOKEN`; accepted verdict is `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION` only |
| 7 | Bayyinah PR gate | ⛔ BLOCKED | runs on PRs; non-approving when secrets absent; merge-block via branch protection UNVERIFIED |
| 8 | Control boundary | ⛔ BLOCKED | needs running runtime for live boundary tests |
| 9 | Device/connectivity pilot | ⬜ NOT_STARTED | needs Phases 4–8 green + allowlisted device + operator |
| 10 | Limited live | ⬜ NOT_STARTED | needs rate limits, monitoring, rollback, error budget, audit export |
| 11 | Full live | ⬜ NOT_STARTED | needs all gates green + no CRITICAL/HIGH + stable smoke + tested incident path |

## Command log summary (patch validation, 2026-06-03 UTC)

| Command | Exit | Label |
|---|---:|---|
| `pytest -q tests/test_modal_activation_tooling.py tests/test_modal_endpoint_token_contract.py tests/test_integrations_control_plane_gates.py -q` | 0 | VERIFIED |
| `python3 .agents/validate.py` | 0 | VERIFIED |
| `python3 -m py_compile .agents/*.py scripts/check-secrets-manifest.py` | 0 | VERIFIED |
| `bash scripts/commander/modal-boundary-gate.sh .` | 0 | VERIFIED (expected WARN for missing runtime secrets) |
| `bash scripts/commander/p0-security-test-gate.sh .` | 0 | VERIFIED (58 tests) |
| `bash scripts/commander/agent-presence-gate.sh` | 0 | VERIFIED (expected WARN for missing runtime secrets) |
| `bash scripts/commander/modal-runtime-smoke.sh` | 2 | VERIFIED fail-closed HOLD: `UNVERIFIED_SECRET_MISSING`, no endpoint contacted |
| `python3 scripts/check-secrets-manifest.py --all` | 1 | VERIFIED fail-closed: 6 required secrets UNSET |
| `python3 scripts/check-secrets-manifest.py --phase endpoint-smoke` | 1 | VERIFIED fail-closed: 4 endpoint-smoke secrets UNSET |
| `python3 scripts/check-secrets-manifest.py --phase bayyinah-pr-gate` | 1 | VERIFIED fail-closed: 2 PR-gate tokens UNSET |
| `npm run test:unit` | 0 | VERIFIED |
| `npm run check` | 0 | VERIFIED |
| `git diff --check` | 0 | VERIFIED |
| `python3 -m pytest -q tests/` | 2 | UNVERIFIED full-suite environment: missing local Python deps `httpx` and `requests` |

## Deploy-trigger audit (no-auto-deploy rule)

| Workflow | `push` can deploy? | Gate | Label |
|---|---|---|---|
| `modal-deploy.yml` | No | `workflow_dispatch` + confirm `DEPLOY_MODAL` + `production` | ✅ VERIFIED |
| `render-deploy.yml` | No | `workflow_dispatch` + confirm `DEPLOY` + `production` | ✅ VERIFIED |
| `modal-runtime-auto-activation.yml` | No | deploy job requires `workflow_dispatch && confirm==ACTIVATE`; push/schedule reach **smoke-only** job | ✅ VERIFIED |

## Prepared (NOT executed) — Phase 4+ commands

```bash
# Phase 2 precheck (per phase):
python3 scripts/check-secrets-manifest.py --phase modal-deploy   # must PASS first

# Phase 4 — Modal deploy (manual, approval-gated; DO NOT auto-run):
#   GitHub → Actions → "modal-deploy" → Run workflow → confirm_deploy = DEPLOY_MODAL
#   (production environment reviewers must approve)

# Phase 5 — Modal CLI smoke (after approved deploy only):
bash scripts/commander/modal-runtime-smoke.sh

# Phase 6 — Endpoint smoke (after deploy; requires live endpoints + split tokens):
#   verify Bayyinah/Mihwar HTTP 200, each endpoint rejects the other endpoint's
#   token, logs expose no secrets, and the workflow emits only:
#   VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION
```

## Blocker list by severity

| Severity | ID | Blocker | Remediation | Owner action |
|---|---|---|---|---|
| HIGH | B1 | Endpoint-token isolation hardening is not launch evidence until merged and CI-reviewed | Merge this hardening PR after checks pass | No (agent-fixed; awaits review/merge) |
| HIGH | B2 | Required Modal/agent secrets UNSET | Provision in GitHub Actions / secret manager | **Yes** |
| HIGH | B3 | No live `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION` run exists | Run manual Modal Runtime Activation after B1/B2 | **Yes** |
| MEDIUM | B4 | Bayyinah PR gate merge-blocking unverified | Confirm branch protection requires the check | **Yes** |
| LOW | B5 | SonarCloud/CodeQL duplicate-run CI noise (env-gated) | Repo CI config cleanup | Yes |

No CRITICAL blockers.

## Verdict

**`HOLD`** — proceed to Phase 4 only after: (1) endpoint-token isolation hardening
is merged and CI-reviewed, (2) the owner provisions `MODAL_TOKEN_ID`,
`MODAL_TOKEN_SECRET`, `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`,
`BAYYINAH_API_TOKEN`, and `MIHWAR_API_TOKEN` with distinct endpoint tokens, and
(3) the owner grants explicit production approval. Re-run
`check-secrets-manifest.py --phase modal-deploy`,
`check-secrets-manifest.py --phase endpoint-smoke`, and the local gates
immediately before activation. The only acceptable live endpoint launch verdict
is `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION`.
