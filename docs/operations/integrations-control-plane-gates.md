# Integrations Control-Plane Gates Runbook

## Verdict

VERIFIED by repository inspection: Copilot cloud agent is not a dependency for this runbook. Use GitHub Issue -> Codex/Claude/local engineer -> PR -> CI -> review when Copilot cloud agent assignment is unavailable.

## Workflow classes

### No-secrets preflight

- `secret-scan`: runs `python scripts/security/static_audit.py .` without external services.
- `Aegis Security Gate`: runs local Aegis verification and Python tests without external AI calls.
- `frontend-sri`: verifies committed frontend integrity metadata.
- `agent-review` boundary steps: run modal and public-surface boundary gates before any optional Modal endpoint review.
- `copilot-setup-steps`: TypeScript-focused setup and tests for Copilot context; no live agent endpoint is required.

### Manual gated deploy

- `modal-deploy`: manual only. The operator must enter `DEPLOY_MODAL`, and Modal token secrets must exist before `modal deploy modal/qarar_rag_infra.py` runs.
- `Modal Runtime Activation`: manual only. It validates local gates first, then optionally deploys or smokes Modal when secrets and dispatch inputs permit it.
- `Qarar FastConnect — Build & Deploy`: build jobs may run on push or pull request; Render deployment runs only from `workflow_dispatch` with `deploy_render=true` and confirmation phrase `DEPLOY_RENDER`.
- `smoke-modal`: manual endpoint smoke only; missing endpoint secrets produce `UNVERIFIED` rather than a source-code success claim.

### Unsafe or needs-remediation

- Any workflow that prints secret values, uses deploy hooks committed in code, deploys on automatic push, disables Aegis, disables secret-scan, or replaces GitHub Secrets with Variables must be treated as unsafe and blocked before merge.
- Live Mihwar/Bayyinah endpoint calls remain optional server-side checks only. Missing secrets are `UNVERIFIED`, not `VERIFIED`.

## Render preflight

- `render.yaml` service: `curlexai-mcp-server`.
- `rootDir`: `.agents/mcp/modal-mcp`.
- `buildCommand`: `npm ci --include=dev && npm run build`.
- `startCommand`: `node dist/server.js`.
- `healthCheckPath`: `/healthz`.
- Secret-bearing values use `sync: false`; do not commit real tokens, deploy hooks, or endpoint secrets.

## Modal preflight

- Qdrant binds to `127.0.0.1` inside `modal/qarar_rag_infra.py`; do not expose the Qdrant REST port publicly.
- Modal Volume is for Qdrant snapshots under `/snapshots`; do not use Modal Volume as live Qdrant storage.
- Public API access must go through HMAC-protected application endpoints, and snapshot creation must remain an explicit API path.

## MCP preflight

- Default Copilot MCP config must point to `.agents/mcp/server_offline.py` with `python3`.
- Do not add live `MIHWAR_ENDPOINT`, `BAYYINAH_ENDPOINT`, Modal URLs, or bearer tokens to Copilot MCP config.
- Remote Render MCP may hold server-side secrets only through provider secret storage, never committed files.

## Verification commands

```bash
python scripts/security/static_audit.py .
python3 scripts/verify_aegis.py
python3 -m pytest -q tests/
git diff --check
npm ci --include=dev
npm run build --if-present
npm test --if-present
```

## Merge recommendation

Merge only after CI passes and reviewers confirm that deploy jobs remain manual, secret-gated, and fail-closed. Do not merge with unresolved `CRITICAL` or `HIGH` findings.
