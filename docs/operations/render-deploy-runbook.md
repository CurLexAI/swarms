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
GitHub → Settings → Environments → production → Environment secrets

Do not store deploy hooks in:

- repository variables
- `.env`
- `render.yaml`
- README files
- docs
- code comments

## Render service settings

Use the Render dashboard to confirm these service settings:

- Root Directory: `.agents/mcp/modal-mcp`
- Build Command: `npm ci --include=dev && npm run build`
- Start Command: `node dist/server.js`
- Health Check Path: `/health`

Runtime secrets for the service belong in Render service environment variables, not in GitHub, except for the single GitHub Environment Secret used to trigger the deploy hook.

## If deploy fails

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
2. `rootDir` points to the service directory that contains `package.json`.
3. Build command matches the service package manager and lockfile.
4. Start command matches the compiled server entrypoint.
5. Health check path returns HTTP 200 without authentication.
6. Required runtime environment variables are present in the Render dashboard.
7. Secret scan output does not report deploy hooks or provider tokens.

## Rotation rule

Treat any old deploy hook named `RENDER_DEPLOY_HOOK` as compromised if it was previously exposed or stored outside protected secrets. Rotate the hook in Render and store only the new `RENDER_DEPLOY_HOOK_URL` value in the protected `production` GitHub Environment secret.
