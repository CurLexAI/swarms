# Launch Readiness — Sovereign Local Runtime Activation Ladder

**Final verdict: `HOLD`**

The official execution path is the **self-hosted Local Ollama runtime**. Modal is
retained only as a **legacy/optional** public runtime path and is no longer a
precondition for readiness. `READY` is forbidden until a real Local Ollama smoke
run verifies reachability, model-set presence, local generation, and no-cloud
egress posture. No live local-runtime evidence exists yet, so the verdict stays
`HOLD` (documentation-only evidence may never yield `READY`).

- Principle: **verification before activation** — no deploy/merge/mutation/live
  control without explicit approval.
- Machine-readable evidence: `docs/launch-evidence/launch-evidence.json`
  (validated by `npm run deploy:evidence:validate`)
- Governance: `docs/launch-evidence/LAUNCH-GOVERNANCE.md`
- Secrets: `docs/launch-evidence/secrets-manifest.md` (+ `.json`, validator)

---

## Runtime-path doctrine

| Path | Role | Consequence |
|---|---|---|
| **Local Ollama runtime** | `OFFICIAL_SOVEREIGN_PATH` | Required for `READY`; its smoke gates the final verdict |
| **Modal** | `LEGACY_OPTIONAL` | Never blocks local sovereign readiness; only gates the public-runtime section |

`scripts/commander/release-readiness-gate.sh` splits its output into three
sections and computes the verdict from them:

1. **Repository Baseline** — static gates, tests, and policy checks (failure ⇒ `BLOCK`).
2. **Local Ollama Runtime** — the official sovereign path (unexecuted or failed
   smoke ⇒ `HOLD`; `READY` is impossible without `LOCAL_OLLAMA_SMOKE=VERIFIED`).
3. **Public Runtime** — Modal (legacy/optional; missing Modal secrets are
   reported as `LEGACY-OPTIONAL` skips and do not hold the verdict) plus
   public-surface header checks.

### Local Ollama HOLD reason codes

| Code | Meaning | Cleared by |
|---|---|---|
| `SELF_HOSTED_OLLAMA_SMOKE_NOT_EXECUTED` | No smoke run reached a live self-hosted Ollama | Running the gate on the sovereign model host with Ollama up |
| `LOCAL_GENERATION_NOT_VERIFIED` | No successful local `/api/generate` round-trip | Non-empty generation response from a manifest model |
| `OLLAMA_NO_CLOUD_NOT_VERIFIED` | Local-only URL + `egress: none_for_inference` posture not confirmed | `OLLAMA_BASE_URL` on the local allowlist and manifest policy intact |
| `LOCAL_MODEL_SET_INCOMPLETE` | Manifest models missing from the live runtime | `scripts/ollama/activate-local-models.sh` passing (18/18 present) |

## Discovery (template vs. this repo)

This repo is the **agent operations & validation layer** (ADR-0001), not the product
monorepo. Several template-referenced paths do not exist here and are
`NOT_APPLICABLE`: `src/server.js`, `src/app.js`, `data/agents/index.json`,
`data/agents/*.yaml`, `backend/app/services/tree_builder.py` (forbidden zone; the
"known indentation blocker" does not exist here). Canonical assets that **do**
exist: `package.json` (`npm run check`, `npm run deploy:evidence:validate`),
`.agents/` (`validate.py`, `modal_app.py`, `config/agents.yaml`),
`agents/registry.yaml` (legacy fallback), `scripts/commander/*` gates,
`scripts/ollama/activate-local-models.sh`, `config/ollama.local.models.json`,
and the deploy/smoke workflows.

## Phase ladder status

| # | Phase | Section | Status | Evidence |
|---|---|---|---|---|
| 1 | Governance | baseline | ✅ VERIFIED | `LAUNCH-GOVERNANCE.md` authored; ADR-0001 + Q8 policy present |
| 2 | Secrets | baseline | ✅ VERIFIED | manifest + validator; `--all` exit=1 fail-closed (names only) |
| 3 | Local gates | baseline | ✅ VERIFIED | `npm run check`/`test`/`build` exit 0; `validate.py`/`py_compile` exit 0; commander gates PASS |
| 4 | **Local Ollama smoke** | **local runtime** | ⛔ **HOLD** | `SELF_HOSTED_OLLAMA_SMOKE_NOT_EXECUTED`, `LOCAL_GENERATION_NOT_VERIFIED`, `OLLAMA_NO_CLOUD_NOT_VERIFIED` |
| 5 | Modal deploy | public (legacy/optional) | ⬜ WAIT | manual, approval-gated; not required for local readiness |
| 6 | Modal CLI smoke | public (legacy/optional) | ⬜ WAIT | depends on Phase 5 |
| 7 | Endpoint smoke | public (legacy/optional) | ⬜ WAIT | accepted verdict remains `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION` only |
| 8 | Bayyinah PR gate | baseline | ⛔ BLOCKED | merge-block via branch protection UNVERIFIED |
| 9 | Control boundary | local runtime | ⛔ BLOCKED | needs running local runtime for live boundary tests |
| 10 | Device/connectivity pilot | local runtime | ⬜ NOT_STARTED | needs Phase 4 green + allowlisted device + operator |
| 11 | Limited live | local runtime | ⬜ NOT_STARTED | needs rate limits, monitoring, rollback, error budget, audit export |
| 12 | Full live | local runtime | ⬜ NOT_STARTED | needs all gates green + no CRITICAL/HIGH + stable smoke + tested incident path |

## Deploy-trigger audit (no-auto-deploy rule)

| Workflow | `push` can deploy? | Gate | Label |
|---|---|---|---|
| `modal-deploy.yml` | No | `workflow_dispatch` + confirm `DEPLOY_MODAL` + `production` | ✅ VERIFIED |
| `render-deploy.yml` | No | `workflow_dispatch` + confirm `DEPLOY` + `production` | ✅ VERIFIED |
| `modal-runtime-auto-activation.yml` | No | deploy job requires `workflow_dispatch && confirm==ACTIVATE`; push/schedule reach **smoke-only** job | ✅ VERIFIED |
| `local-model-smoke.yml` | No | `workflow_dispatch` only, self-hosted runner only | ✅ VERIFIED |

## Prepared (NOT executed) — Local Ollama smoke commands

```bash
# On the sovereign model host (self-hosted; Ollama must be running locally):
docker compose up -d ollama                      # or a native local ollama serve

# Model-set presence against config/ollama.local.models.json (18 models):
bash scripts/ollama/activate-local-models.sh     # OLLAMA_PULL=1 to pull missing

# Full three-section readiness gate (emits LOCAL_OLLAMA_SMOKE=VERIFIED|HOLD):
bash scripts/commander/release-readiness-gate.sh .

# Legacy/optional Modal path (only with explicit approval + secrets present):
#   GitHub → Actions → "modal-deploy" → Run workflow → confirm_deploy = DEPLOY_MODAL
```

## Blocker list by severity

| Severity | ID | Blocker | Remediation | Owner action |
|---|---|---|---|---|
| HIGH | B1 | `SELF_HOSTED_OLLAMA_SMOKE_NOT_EXECUTED` — no live Local Ollama smoke run exists | Run the readiness gate on the sovereign model host | **Yes** |
| HIGH | B2 | `LOCAL_GENERATION_NOT_VERIFIED` — no verified local generation round-trip | Same smoke run; requires a pulled manifest model | **Yes** |
| HIGH | B3 | `OLLAMA_NO_CLOUD_NOT_VERIFIED` — no-cloud posture not live-confirmed | Same smoke run with local-only `OLLAMA_BASE_URL` | **Yes** |
| MEDIUM | B4 | Bayyinah PR gate merge-blocking unverified | Confirm branch protection requires the check | **Yes** |
| MEDIUM | B5 | Legacy/optional Modal path unexecuted (deploy/CLI/endpoint smokes) | Only if the Modal path is still wanted; not required for local readiness | Yes (optional) |
| LOW | B6 | SonarCloud/CodeQL duplicate-run CI noise (env-gated) | Repo CI config cleanup | Yes |

No CRITICAL blockers beyond the standing rule that limited/full live stay
blocked until every prior gate is verified.

## Standing restrictions (unchanged on this branch)

- No deploy. No merge. No secrets committed or echoed. No production activation.
- `READY` requires: zero `BLOCK` failures, `LOCAL_OLLAMA_SMOKE=VERIFIED`, and
  zero remaining `HOLD` flags — enforced by both
  `scripts/commander/release-readiness-gate.sh` and
  `scripts/validate-launch-evidence.mjs`.

## Verdict

**`HOLD`** — proceed only after a real Local Ollama smoke run on the sovereign
model host clears `SELF_HOSTED_OLLAMA_SMOKE_NOT_EXECUTED`,
`LOCAL_GENERATION_NOT_VERIFIED`, and `OLLAMA_NO_CLOUD_NOT_VERIFIED`. The
legacy/optional Modal path may be exercised later under explicit approval; its
only acceptable live endpoint verdict remains
`VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION`.
