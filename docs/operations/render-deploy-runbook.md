# Render Deploy Runbook

## Mode

Render deploy is manual and gated. The repository supports two separate stages:

1. `render-preflight`: no-secrets validation that never calls Render.
2. `render-deploy`: manual production deploy that uses one protected GitHub Environment secret.

## No-Secrets Preflight

`render-preflight` runs on pull requests, pushes to `main`, and manual dispatches. It does not call Render and does not require secrets.

It validates:

- `render.yaml` syntax when the Blueprint is present.
- Render service path existence.
- Absence of deploy hooks and secret-like markers in `render.yaml`.
- Node, Python, Docker, or static project detection.
- Build and tests where the detected runtime exposes them.

## Production Deploy

`render-deploy` runs only via `workflow_dispatch` and is bound to the protected `production` GitHub Environment.

Required secret:

- `RENDER_DEPLOY_HOOK_URL`

Secret location:

- GitHub → Settings → Environments → production → Environment secrets

Do not store deploy hooks in:

- Repository variables.
- `.env` files.
- `render.yaml`.
- README files.
- Documentation examples.
- Code comments.

## Render Service Settings

For the current Modal MCP Gateway Blueprint, Render should use:

- Service name: `curlexai-mcp-server`
- Root directory: `.agents/mcp/modal-mcp`
- Build command: `npm ci --include=dev && npm run build`
- Start command: `node dist/server.js`
- Health check path: `/health`

Runtime secrets for the service belong in the Render dashboard, not in GitHub, except for the single deploy-hook secret used by the gated workflow.

## If Deploy Fails

Check in order:

1. Render service build logs.
2. Root directory.
3. Package manager lockfile.
4. Build command.
5. Start command.
6. Health check path.
7. Missing runtime environment variables in the Render dashboard.
8. Secret scan output.

Treat any previous deploy hook value as compromised if it appeared in a local environment file, Actions log, issue, PR, or documentation. Rotate it in Render and store only the new value as `RENDER_DEPLOY_HOOK_URL` in the protected `production` GitHub Environment.
