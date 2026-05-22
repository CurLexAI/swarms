# Render MCP Integration

This document explains how to connect the local MCP server configuration with a remote Render-hosted MCP endpoint, enabling remote clients (ChatGPT, Claude web, etc.) to access the CurLexAI agents (Mihwar and Bayyinah) through the MCP protocol.

---

## Architecture

```
ChatGPT / Claude Web / Remote Client
  ↓
https://mcp.render.com/mcp
  ↓
Render Web Service (Node.js MCP Server)
  ├── Modal API (deployment info, logs)
  └── CurLexAI Agents (Mihwar, Bayyinah)
      ├── MIHWAR_ENDPOINT → DeepSeek-Coder-V2-Instruct
      └── BAYYINAH_ENDPOINT → Qwen2.5-Coder-32B-Instruct
```

The remote MCP server bridges ChatGPT/Claude with both:
1. **Modal deployment APIs** — read-only tools for deployment status, logs, and safe inference
2. **CurLexAI agent endpoints** — Mihwar (code generation) and Bayyinah (code review)

---

## Deployment to Render

### Prerequisites

- GitHub repository connected to Render
- Modal API token with read-only scope
- CurLexAI agent endpoints (Mihwar, Bayyinah) active in Modal
- CurLexAI agent API token (if required)

### Step 1: Create a New Web Service on Render

1. Go to https://dashboard.render.com/
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Fill in the configuration:

| Field | Value |
|-------|-------|
| **Name** | `curlexai-mcp-server` |
| **Root Directory** | `.agents/mcp/modal-mcp` |
| **Runtime** | `Node` |
| **Build Command** | `npm install && npm run build` |
| **Start Command** | `node dist/server.js` |
| **Plan** | Free or Starter (whichever fits) |

### Step 2: Configure Environment Variables

Set the following secrets in Render dashboard (**Environment** tab):

| Variable | Value | Required |
|----------|-------|----------|
| `MCP_BASE_URL` | `https://curlexai-mcp-server.onrender.com` | ✓ |
| `MCP_BEARER_TOKEN` | Generate a strong token | ✓ |
| `MODAL_API_TOKEN` | Your Modal API token | ✓ |
| `MODAL_API_BASE_URL` | `https://api.modal.com` | ✓ |
| `MIHWAR_ENDPOINT` | `https://curlexai--mihwar-generate.modal.run` | |
| `BAYYINAH_ENDPOINT` | `https://curlexai--bayyinah-review.modal.run` | |
| `AGENT_API_TOKEN` | Your CurLexAI agent API token (if required) | |
| `ENABLE_MUTATING_TOOLS` | `false` | |
| `NODE_ENV` | `production` | |

### Step 3: Deploy

Click **"Create Web Service"**. Render will:
- Clone the repo
- Run `npm install && npm run build`
- Start the Node server
- Assign a URL: `https://curlexai-mcp-server.onrender.com`

Monitor logs in the Render dashboard to confirm deployment succeeded.

### Step 4: Verify the Server

```bash
# Test the /healthz endpoint
curl https://curlexai-mcp-server.onrender.com/healthz

# Test the /sse endpoint with auth
curl -H "Authorization: Bearer <MCP_BEARER_TOKEN>" \
  https://curlexai-mcp-server.onrender.com/sse
```

You should receive a 200 response with `{"status":"ok"}`.

---

## Using the Remote MCP Server

### ChatGPT Configuration

1. In ChatGPT, open **Settings** → **MCP Servers**
2. Click **"Add MCP Server"**
3. Fill in:
   - **Name**: `CurLexAI Agents`
   - **URL**: `https://curlexai-mcp-server.onrender.com/sse`
   - **Auth Header**: `Bearer <MCP_BEARER_TOKEN>`
4. Click **"Save"**

ChatGPT will now have access to:
- `mihwar_generate` — Ask Mihwar to generate code for a task
- `bayyinah_review` — Ask Bayyinah to review code
- `modal_list_deployments` — Check Modal deployment status
- `modal_get_recent_logs` — View deployment logs
- Other read-only Modal tools

### Claude Web Configuration

1. In claude.ai settings (if MCP support is available), add:
   ```json
   {
     "mcpServers": {
       "curlexai-agents": {
         "url": "https://curlexai-mcp-server.onrender.com/sse",
         "auth": "Bearer <MCP_BEARER_TOKEN>"
       }
     }
   }
   ```

---

## Tool Reference

### Agent Tools

#### `mihwar_generate`
Generate code using the Mihwar model.

**Parameters:**
- `task` (string, required): The task description
- `code` (string, optional): Existing code to modify
- `context` (string, optional): Additional context

**Example:**
```json
{
  "tool": "mihwar_generate",
  "args": {
    "task": "Add error handling to this function",
    "code": "function process(data) { return data.map(x => x * 2); }",
    "context": "This is a data processing pipeline"
  }
}
```

#### `bayyinah_review`
Review code using the Bayyinah model.

**Parameters:**
- `code` (string, required): Code to review
- `context` (string, optional): Review criteria or context

**Example:**
```json
{
  "tool": "bayyinah_review",
  "args": {
    "code": "function add(a, b) { return a + b; }",
    "context": "Check for security issues and test coverage"
  }
}
```

### Modal Tools

- `modal_list_apps` — List Modal applications
- `modal_list_deployments` — List all deployments
- `modal_get_deployment_status` — Check specific deployment status
- `modal_list_model_endpoints` — List model serving endpoints
- `modal_get_recent_logs` — Fetch deployment logs
- `modal_run_safe_inference` — Run safe inference on a model endpoint

---

## Troubleshooting

### 502 Bad Gateway
- Check Render logs: `Status` → `Logs`
- Verify environment variables are set correctly
- Ensure `node dist/server.js` runs without errors locally:
  ```bash
  cd .agents/mcp/modal-mcp
  npm install && npm run build
  PORT=8787 node dist/server.js
  ```

### 401 Unauthorized (ChatGPT)
- Confirm `MCP_BEARER_TOKEN` is set in Render environment
- Make sure the Bearer token matches exactly in ChatGPT settings
- Check that the auth header format is: `Authorization: Bearer <token>`

### Agent Tools Return Errors
- Verify `MIHWAR_ENDPOINT` and `BAYYINAH_ENDPOINT` are active in Modal
- Check `AGENT_API_TOKEN` is correct (if required)
- Review Render logs for HTTP error details from the agent endpoints

### Deployment Failed (Build Error)
- Confirm `.agents/mcp/modal-mcp/package.json` exists
- Check that TypeScript compiles: `npm run check` in the modal-mcp directory
- Ensure `tsconfig.json` is properly configured

---

## Local Development

To test the server locally before deploying:

```bash
cd .agents/mcp/modal-mcp

# Install dependencies
npm install

# Type-check
npm run check

# Build
npm run build

# Run locally on port 8787
export MCP_BASE_URL=http://localhost:8787
export MCP_BEARER_TOKEN=test-token-123
export MODAL_API_TOKEN=<your-token>
export MODAL_API_BASE_URL=https://api.modal.com
export MIHWAR_ENDPOINT=https://curlexai--mihwar-generate.modal.run
export BAYYINAH_ENDPOINT=https://curlexai--bayyinah-review.modal.run

PORT=8787 node dist/server.js

# In another terminal, test the server
curl -H "Authorization: Bearer test-token-123" \
  http://localhost:8787/healthz
```

---

## Security Notes

- **Bearer tokens** are never logged or exposed in error messages
- **Modal endpoints** remain backend-only; client models see only tool names
- **Agent tokens** are validated on every request; never passed to the client
- **Mutating tools are disabled** by default and require `ENABLE_MUTATING_TOOLS=true` + explicit approval
- All communication with Modal and agent endpoints uses HTTPS

---

## Integration with Local MCP Server

This remote server **complements** the local MCP server (`.agents/mcp/server.py`):

| Server | Clients | Setup | Use Case |
|--------|---------|-------|----------|
| **Local** (server.py) | GitHub Copilot, Claude Desktop, Cursor | Local Python process + Copilot MCP config | Integrated development, private setup |
| **Remote** (Render) | ChatGPT, Claude web, remote tools | Render Web Service + HTTPS endpoint | Public APIs, shared team access, ChatGPT integration |

Both servers expose the same `mihwar_generate` and `bayyinah_review` tools but use different transports.

---

## References

- [Render Web Service Documentation](https://render.com/docs/web-services)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [CurLexAI Agents Handbook](../../AGENTS.md)
- [Local MCP Setup](./README.md)
