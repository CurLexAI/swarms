# modal-mcp (scaffold)

Read-only MCP scaffold to connect MCP-capable remote clients to Modal project surfaces over **HTTPS/SSE**. In Render, this service is the `curlexai-mcp-server` Modal MCP Gateway; it is not the BSM backend and not a public product API gateway.

## Scope

- No runtime modifications to existing repository services.
- No changes to current Modal deployment configuration.
- No real secrets are included.
- Mutating tools exist as **disabled stubs** only.

## Exposed read-only tools

- `modal_list_apps`
- `modal_list_deployments`
- `modal_get_deployment_status`
- `modal_list_model_endpoints`
- `modal_get_recent_logs`
- `modal_run_safe_inference`
- `modal_list_tools`

## Mutating tools (disabled by default)

- `modal_deploy`
- `modal_update_gpu`
- `modal_update_secrets`
- `modal_delete_app`
- `modal_change_endpoint`

Mutating tools require both:
1. `ENABLE_MUTATING_TOOLS=true`
2. request payload containing `explicitApproval: true`

## Local run

```bash
cd .agents/mcp/modal-mcp
npm install
npm run check
npm run build
PORT=8787 node dist/server.js
```

## Deploy on Cloudflare Workers (guide)

1. Keep this scaffold as reference logic, then adapt request handling to Worker `fetch` runtime.
2. Set secrets in Worker settings (do not commit them):
   - `MCP_BEARER_TOKEN`
   - `MODAL_API_TOKEN`
3. Expose one HTTPS route for `/sse` and one for `/healthz`.
4. Enforce bearer authentication before tool dispatch.

## Deploy on Render (guide)

1. Use the repository Blueprint service named `curlexai-mcp-server`.
2. Root directory: `.agents/mcp/modal-mcp`
3. Build command: `npm ci --include=dev && npm run build`
4. Start command: `node dist/server.js`
5. Health check path: `/healthz` (unauthenticated, returns `{ "status": "ok" }`, and must not call Modal or private agents).
6. Add environment variables from `.env.example` using Render dashboard secrets. Keep `MIHWAR_ENDPOINT`, `BAYYINAH_ENDPOINT`, `MODAL_API_TOKEN`, and `AGENT_API_TOKEN` server-side only.
7. Keep `ENABLE_MUTATING_TOOLS=false` unless explicitly approved.

The BSM backend is intentionally external to this service. Do not add product backend routes or public API gateway behavior to `modal-mcp`.

## ChatGPT MCP connector shape

Use HTTPS endpoint:

- Base URL: `https://<your-domain>/sse`
- Auth: Bearer token (same value as `MCP_BEARER_TOKEN`)

