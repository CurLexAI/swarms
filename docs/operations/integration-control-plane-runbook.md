# Integration Control-Plane Runbook

## Verdict

The repository separates no-secrets validation from deployment actions. Render preflight is safe for pull requests and pushes. Render deploy is manual only, production-environment gated, and backed by `RENDER_DEPLOY_HOOK_URL` from GitHub Environment secrets.

## Workflow classification

| Workflow | Class | Secret access | Deployment authority |
| --- | --- | --- | --- |
| `.github/workflows/render-preflight.yml` | no-secrets preflight | No | No |
| `.github/workflows/render-deploy.yml` | manual gated deploy | `RENDER_DEPLOY_HOOK_URL` from `production` environment secrets | Yes, only after manual `DEPLOY` confirmation |
| `.github/workflows/qarar-fastconnect-deploy.yml` | no-secrets build preflight | No Render secrets | No Render deploy |
| `.github/workflows/modal-deploy.yml` | manual or main-path Modal deploy | Modal secrets | Modal only |
| `.github/workflows/modal-runtime-activation.yml` | manual runtime activation | Modal and agent runtime secrets | Optional Modal deploy/smoke only by workflow input |
| `.github/workflows/secret-scan.yml` | no-secrets security gate | No | No |
| `.github/workflows/aegis-gate.yml` | no-secrets security gate | No external AI key use; AI key names are nullified | No |

## Render operating rules

1. Keep `render.yaml` as a blueprint only. Do not place deploy hooks, Render API tokens, or service IDs in the repository.
2. Use `.github/workflows/render-preflight.yml` for PR/push validation of the Render blueprint, SR.BSM public server, and CDN SRI checks.
3. Use `.github/workflows/render-deploy.yml` only through `workflow_dispatch`.
4. Store `RENDER_DEPLOY_HOOK_URL` only as a GitHub Environment secret named `production`.
5. Do not store the deploy hook as a repository variable or in `.env` files.
6. Do not reintroduce automatic Render deployment in build workflows.

## Modal and MCP boundaries

- Modal endpoints remain backend-only and are not exposed to browser or iPhone clients.
- MCP/Copilot no-secrets mode remains the safe default for repository work.
- Qdrant snapshot persistence may use a Modal Volume mounted at `/snapshots`; live Qdrant storage remains local container storage at `/qdrant/storage` and is not mounted as a Modal Volume.

## Verification commands

```bash
python3 scripts/security/static_audit.py .
python3 scripts/verify_aegis.py
python3 -m pytest -q tests/
git diff --check
npm run test:render-public
npm run check
npm run check:swarms-presence:strict
npm run build --if-present
npm test --if-present
bash -n .github/workflows/render-deploy.yml || true
```

## Remaining operator checks

- Confirm the `production` GitHub Environment requires human reviewers before `render-deploy.yml` can run.
- Confirm `RENDER_DEPLOY_HOOK_URL` exists only in GitHub Environment secrets.
- Run `npm run check:swarms-presence:strict` only for release/readiness evidence; the no-network `npm run check:swarms-presence` path is local validation, not runtime readiness.
- Confirm any live Render/Vercel/Modal dashboards match the repository runbooks before production changes.

## Runtime policy source of truth

`src/policy/runtime-policy.ts` is the canonical runtime policy. `src/runtimePolicy.ts` is a deprecated compatibility adapter only and must not define an independent provider registry or routing order.
