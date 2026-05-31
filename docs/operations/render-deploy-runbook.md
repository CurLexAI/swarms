# Render Deploy Runbook

## Mode

Render deploy is manual and gated. Repository automation is split into a no-secrets preflight stage and a protected production deploy stage.

## No-secrets preflight

`render-preflight` runs on pull requests, pushes to `main`, and manual dispatch. It does not call Render and does not require secrets.

It validates:

- `render.yaml` syntax when the Blueprint file is present.
- No deploy hooks, provider tokens, or obvious secret markers are committed to `render.yaml`.
- The Render service `rootDir` exists.
- The detected Node, Python, Docker, or static build path can run the applicable local checks.
- The configured Render health check path points to a repository-owned unauthenticated health endpoint.

## Production deploy

`render-deploy` runs only via `workflow_dispatch` and the protected `production` GitHub Environment.

Required secret:

- `RENDER_DEPLOY_HOOK_URL`

Secret location:

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
2. `rootDir` points to the service directory that contains `package.json`.
3. Build command matches the service package manager and lockfile.
4. Start command matches the compiled server entrypoint.
5. Health check path returns HTTP 200 without authentication.
6. Required runtime environment variables are present in the Render dashboard.
7. Secret scan output does not report deploy hooks or provider tokens.

## Rotation rule

Treat any old deploy hook named `RENDER_DEPLOY_HOOK` as compromised if it was previously exposed or stored outside protected secrets. Rotate the hook in Render and store only the new `RENDER_DEPLOY_HOOK_URL` value in the protected `production` GitHub Environment secret.
