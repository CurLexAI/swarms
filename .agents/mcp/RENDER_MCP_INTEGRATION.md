# Render MCP Integration

This document defines the Render deployment contract for this repository. It separates the Render-hosted MCP/agent-control runtime from the BSM product backend so that operators do not confuse infrastructure tooling with an application origin service.

---

## Render Service Contract

| Concern | Render service in this repo | Status | Notes |
|---|---|---|---|
| MCP / agent-control gateway | `curlexai-mcp-server` | Defined in `render.yaml` | Node.js HTTPS/SSE service rooted at `.agents/mcp/modal-mcp`. It exposes MCP tool transport and performs server-side calls to Modal APIs and private agent endpoints. |
| BSM backend | None | Intentionally external | The BSM application/backend source is not present in `CurLexAI/swarms`; this repository is the agent operations layer. Do not add BSM routes or product backend source here. |
| API gateway for public product traffic | None | Intentionally external | Product/browser API traffic must be owned by the BSM or product-origin repository, not by the MCP service. |
| Other origin service | None | Not defined | Add a distinct `render.yaml` service only when the owning source tree exists in this repository and passes ADR-0001 boundary review. |

`curlexai-mcp-server` is therefore a **Modal MCP Gateway**, not the BSM backend and not a general public API gateway.

---

## Architecture

```text
MCP-capable remote client
  ↓ HTTPS/SSE with Bearer auth
Render Web Service: curlexai-mcp-server
  ├── /healthz        public unauthenticated Render health probe
  └── /sse            authenticated MCP tool transport
       ├── Modal API  server-side deployment/log read tools
       └── CurLexAI private agents server-side only
           ├── MIHWAR_ENDPOINT  configured as a Render secret/env var
           └── BAYYINAH_ENDPOINT configured as a Render secret/env var
```

Private agent endpoints stay behind the Render service. Browser, iPhone, frontend code, and public product clients must never receive Modal URLs, Modal tokens, or `AGENT_API_TOKEN` values.

---

## Deployment to Render

### Prerequisites

- GitHub repository connected to Render.
- Modal API token with the minimum scope needed for the read-only Modal tools.
- CurLexAI private agent endpoints active server-side when agent tools are enabled.
- CurLexAI agent API token only in Render secret/environment storage when the private agent endpoints require it.

### Blueprint-backed service

`render.yaml` is the source of truth for this repository's Render service:

| Field | Value |
|---|---|
| Service name | `curlexai-mcp-server` |
| Service role | Modal MCP Gateway / agent-control gateway |
| Root directory | `.agents/mcp/modal-mcp` |
| Runtime | Node |
| Build command | `npm ci --include=dev && npm run build` |
| Start command | `node dist/server.js` |
| Port | `8787` |
| Health check path | `/healthz` |

Do not rename the service in documentation without updating `render.yaml`, `MCP_BASE_URL`, and any MCP client configuration in the same change.

### Environment variables

Set secret values in the Render dashboard or approved secret manager. Do not print them in logs, PR comments, tickets, or screenshots.

| Variable | Purpose | Required | Exposure boundary |
|---|---|---:|---|
| `MCP_BASE_URL` | Public HTTPS base URL for the MCP gateway itself | Yes | May be visible to MCP clients. |
| `MCP_BEARER_TOKEN` | Bearer token required for `/sse` | Yes | Secret; never log or return. |
| `MODAL_API_TOKEN` | Server-side Modal API access for read-only Modal tools | Yes | Secret; Render server-side only. |
| `MODAL_API_BASE_URL` | Modal API origin, normally `https://api.modal.com` | Yes | Not a secret, but keep server-side. |
| `MIHWAR_ENDPOINT` | Private Mihwar endpoint URL | No | Secret-like private endpoint; Render server-side only. |
| `BAYYINAH_ENDPOINT` | Private Bayyinah endpoint URL | No | Secret-like private endpoint; Render server-side only. |
| `AGENT_API_TOKEN` | Token used by private agent endpoints | No | Secret; Render server-side only. |
| `ENABLE_MUTATING_TOOLS` | Controls disabled mutating tool stubs | No | Keep `false` unless a separate approved change enables writes. |
| `MODAL_DEPLOYMENT_ALLOWLIST` | Optional comma-separated deployment ID allow-list | No | Treat deployment identifiers as operational metadata. |
| `MAX_LOG_LINES` | Maximum log lines returned by log tool | No | Use bounded values only. |
| `NODE_ENV` | Runtime mode | Yes | `production`. |

Use placeholders such as `<server-side-mihwar-endpoint>` in documentation and examples. Do not paste real `*.modal.run` URLs or tokens into deployment logs or documentation.

---

## Health-check Expectations

| Render service | Path | Authentication boundary | Expected response shape | Purpose |
|---|---|---|---|---|
| `curlexai-mcp-server` | `GET /healthz` | Unauthenticated. It must not call Modal, private agents, or any external API. | HTTP `200` with JSON object `{"status":"ok"}`. | Render liveness/readiness probe for the Node process only. |
| `curlexai-mcp-server` | `GET /sse` | Requires `Authorization: Bearer <MCP_BEARER_TOKEN>`. | HTTP `200`, `Content-Type: text/event-stream`, an initial ready event containing `{"status":"ok"}`. | Authenticated MCP transport check; validates the bearer boundary without exposing private endpoints. |
| BSM backend | Not defined in this repo | Owned by the external BSM/product-origin service. | Must be documented in the BSM repository or deployment blueprint. | This repository cannot verify or define BSM backend health until the BSM source/Render blueprint is supplied. |
| Public product API gateway | Not defined in this repo | Owned by the product-origin/API-gateway service. | Must be documented with the owning service. | Prevents accidental use of the MCP service as a public product API gateway. |

A passing `/healthz` only proves that the Render MCP process started. It does **not** prove Modal reachability, private agent runtime health, BSM backend health, or end-to-end product readiness.

---

## Verification Commands

Use sanitized commands only. Replace tokens locally from your secret manager; never paste token values into command history shared with others.

```bash
# Render process health; no auth, no Modal call expected.
curl https://curlexai-mcp-server.onrender.com/healthz

# MCP transport boundary; requires bearer auth.
curl -H "Authorization: Bearer ${MCP_BEARER_TOKEN}" \
  https://curlexai-mcp-server.onrender.com/sse
```

Expected `/healthz` body:

```json
{"status":"ok"}
```

Expected unauthenticated `/sse` behavior: HTTP `401` with no private endpoint details.

---

## Using the Remote MCP Server

### ChatGPT / remote MCP client configuration

Configure only the Render MCP gateway URL and the MCP bearer token:

- **Name**: `CurLexAI Modal MCP Gateway`
- **URL**: `https://curlexai-mcp-server.onrender.com/sse`
- **Auth header**: `Bearer <MCP_BEARER_TOKEN>`

The client may see tool names such as `mihwar_generate`, `bayyinah_review`, `modal_list_deployments`, and `modal_get_recent_logs`. The client must not see `MIHWAR_ENDPOINT`, `BAYYINAH_ENDPOINT`, `MODAL_API_TOKEN`, or `AGENT_API_TOKEN` values.

---

## Tool Reference

### Agent tools

#### `mihwar_generate`

Generate implementation guidance using the server-side Mihwar endpoint.

Parameters:

- `task` (string, required): The task description.
- `code` (string, optional): Existing code to modify.
- `context` (string, optional): Additional context.

#### `bayyinah_review`

Review code using the server-side Bayyinah endpoint.

Parameters:

- `code` (string, required): Code to review.
- `context` (string, optional): Review criteria or context.

### Modal tools

- `modal_list_apps` — list Modal applications.
- `modal_list_deployments` — list deployments.
- `modal_get_deployment_status` — check a deployment status.
- `modal_list_model_endpoints` — list model-serving endpoints.
- `modal_get_recent_logs` — fetch bounded deployment logs.
- `modal_run_safe_inference` — run policy-filtered safe inference on a model endpoint.

Mutating tool names are scaffolded but disabled by default. Enabling them requires a separate approved change, explicit operator approval, and a rollback plan.

---

## Troubleshooting

### 502 Bad Gateway

- Check Render service logs for startup errors without printing env values.
- Verify required environment variables are configured, but do not echo values.
- Rebuild locally from `.agents/mcp/modal-mcp` with `npm ci --include=dev && npm run build`.

### 401 Unauthorized

- Confirm `MCP_BEARER_TOKEN` exists in Render secret/environment storage.
- Confirm the client sends `Authorization: Bearer <token>`.
- Do not paste the token into issue comments, PR text, screenshots, or logs.

### Agent tools return errors

- Verify private agent endpoints from a trusted backend shell only.
- Confirm `AGENT_API_TOKEN` is configured when required.
- Review Render logs only for sanitized status/error codes; do not log endpoint URLs, request bodies, or tokens.

### BSM health is requested

- Treat it as `UNVERIFIED` in this repository unless the external BSM service contract or source tree is supplied.
- Do not add BSM backend routes to `CurLexAI/swarms`; this repository remains the agent operations layer.

---

## Local Development

```bash
cd .agents/mcp/modal-mcp
npm ci --include=dev
npm run check
npm run build

export MCP_BASE_URL=http://localhost:8787
export MCP_BEARER_TOKEN=test-token-123
export MODAL_API_TOKEN=placeholder-modal-token
export MODAL_API_BASE_URL=https://api.modal.com
# Optional private endpoints stay local/server-side only:
# export MIHWAR_ENDPOINT=<server-side-mihwar-endpoint>
# export BAYYINAH_ENDPOINT=<server-side-bayyinah-endpoint>
# export AGENT_API_TOKEN=<server-side-agent-token>

PORT=8787 node dist/server.js
```

---

## Security Notes

- Bearer tokens are never logged or exposed in error messages.
- Modal and private agent endpoints remain server-side only; client models see tool names, not endpoint URLs.
- Agent tokens are never passed to clients.
- `/healthz` must remain dependency-free and unauthenticated so it cannot leak private runtime state.
- Mutating tools remain disabled by default and require both `ENABLE_MUTATING_TOOLS=true` and request-level explicit approval before any future implementation.
- All Modal and agent calls use HTTPS from the Render service only.

---

## Integration with Local MCP Server

This remote service complements the local MCP server (`.agents/mcp/server.py`):

| Server | Clients | Setup | Use case |
|---|---|---|---|
| Local stdio MCP (`server.py`) | GitHub Copilot, Claude Desktop, Cursor | Local Python process + env from a trusted shell | Integrated development and private workstation use. |
| Remote Render MCP (`curlexai-mcp-server`) | ChatGPT, Claude web, remote tools | Render Web Service + HTTPS/SSE endpoint | Remote MCP access through a server-side Modal MCP Gateway. |
| BSM backend | Product/browser clients | External BSM/product-origin deployment | Product application APIs; not defined by this repo. |

Both MCP servers can expose `mihwar_generate` and `bayyinah_review`, but they use different transports and must keep private agent endpoints out of client-visible configuration.

---

## References

- [Render Web Service Documentation](https://render.com/docs/web-services)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [CurLexAI Agents Handbook](../../AGENTS.md)
- [Local MCP Setup](./README.md)
