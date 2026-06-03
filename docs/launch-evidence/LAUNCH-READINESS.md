# Launch Readiness — Qarar / Bayyinah Activation Ladder

**Final verdict: `HOLD`**

Phases 1–3 are complete and verified on `main` (with two gate fixes pending in open
PR #336). Phases 4–11 are blocked pending owner-provisioned secrets and explicit
production approval. No live runtime evidence exists, so `READY` is not permissible
(documentation-only evidence may never yield `READY`).

- Base: `main` @ `6795e88a54f9d6d876deda406c0254f4a973e48a`
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
| 3 | Local gates | 🟡 PARTIAL | `npm run check`/`test`/`build` exit 0; `validate.py`/`py_compile` exit 0; commander gates PASS **except** qala-egress + pytest collection — both fixed in **#336** |
| 4 | Modal deploy | ⛔ BLOCKED | prepared command below; needs `MODAL_TOKEN_*` + approval |
| 5 | Modal CLI smoke | ⛔ BLOCKED | depends on Phase 4 |
| 6 | Endpoint smoke | ⛔ BLOCKED | needs `BAYYINAH_ENDPOINT`/`MIHWAR_ENDPOINT` plus `BAYYINAH_API_TOKEN`/`MIHWAR_API_TOKEN` live and cross-token negative smoke passing |
| 7 | Bayyinah PR gate | ⛔ BLOCKED | runs on PRs; non-approving when secrets absent; merge-block via branch protection UNVERIFIED |
| 8 | Control boundary | ⛔ BLOCKED | needs running runtime for live boundary tests |
| 9 | Device/connectivity pilot | ⬜ NOT_STARTED | needs Phases 4–8 green + allowlisted device + operator |
| 10 | Limited live | ⬜ NOT_STARTED | needs rate limits, monitoring, rollback, error budget, audit export |
| 11 | Full live | ⬜ NOT_STARTED | needs all gates green + no CRITICAL/HIGH + stable smoke + tested incident path |

## Command log summary (Phase 3, this run)

| Command | Exit | Label |
|---|---|---|
| `python3 .agents/validate.py` | 0 | VERIFIED |
| `python3 -m py_compile .agents/*.py …` | 0 | VERIFIED |
| `npm ci` | 0 | VERIFIED |
| `npm run check` | 0 | VERIFIED (8/0) |
| `npm test` | 0 | VERIFIED |
| `npm run build` (tsc) | 0 | VERIFIED |
| `adr-0001-boundary-gate.sh` | 0 | VERIFIED |
| `modal-boundary-gate.sh` | 0 | VERIFIED |
| `p0-security-test-gate.sh` | 0 | VERIFIED (58 tests) |
| `agent-presence-gate.sh` | 0 | VERIFIED |
| `qala-audit-integrity-gate.sh` | 0 | VERIFIED |
| `qala-egress-residency-gate.sh` | 1 | BLOCKED (fixed in #336) |
| `pytest -q tests/` | 2 | BLOCKED (fixed in #336) |
| `check-secrets-manifest.py --all` | 1 | VERIFIED (fail-closed, expected) |

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

# Phase 6 — Endpoint smoke (after deploy; requires live endpoints + token):
#   verify Bayyinah/Mihwar HTTP 200, authed request succeeds, invalid token fails,
#   logs expose no secrets.
```

## Blocker list by severity

| Severity | ID | Blocker | Remediation | Owner action |
|---|---|---|---|---|
| HIGH | B1 | `aegis-verify` red on `main` (pytest collection + qala-egress) | Merge **PR #336** | No (agent-fixed; awaits review/merge) |
| HIGH | B2 | Required Modal/agent secrets UNSET | Provision in GitHub Actions / secret manager | **Yes** |
| MEDIUM | B3 | Bayyinah PR gate merge-blocking unverified | Confirm branch protection requires the check | **Yes** |
| LOW | B4 | SonarCloud/CodeQL duplicate-run CI noise (env-gated) | Repo CI config cleanup | Yes |

No CRITICAL blockers.

## Verdict

**`HOLD`** — proceed to Phase 4 only after: (1) PR #336 merged (clears B1), and
(2) owner provisions required secrets (clears B2) and grants explicit production
approval. Re-run `check-secrets-manifest.py --phase modal-deploy` and the local
gates immediately before activation.
