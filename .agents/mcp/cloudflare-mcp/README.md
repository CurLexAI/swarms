# CurLexAI Remote MCP Server (Cloudflare Workers)

Remote [Model Context Protocol](https://modelcontextprotocol.io/) server deployed on Cloudflare Workers, providing authenticated access to CurLexAI agent operations.

## Tools

| Tool | Description |
|------|-------------|
| `mihwar_generate` | Generate code/architecture using the Mihwar agent (DeepSeek-Coder-V2-Instruct) |
| `bayyinah_review` | Review code using the Bayyinah agent (Qwen2.5-Coder-32B-Instruct) |
| `pipeline` | Run Mihwar→Bayyinah pipeline (generate then review) |
| `agent_info` | List configured CurLexAI agents, models, roles, and tiers |
| `whoami` | Show the authenticated GitHub user |

## Architecture

```
MCP Client (Claude/Cursor/Inspector)
  → GitHub OAuth (workers-oauth-provider)
  → Cloudflare Worker (this server)
  → Modal agent endpoints (backend-only, never exposed to clients)
```

## Local Development

### Prerequisites

- Node.js >= 20
- A [GitHub OAuth App](https://github.com/settings/developers) for local dev
  - Homepage URL: `http://localhost:8788`
  - Callback URL: `http://localhost:8788/callback`

### Setup

```bash
cd .agents/mcp/cloudflare-mcp
npm install

# Create .env with your GitHub OAuth credentials
cp .env.example .env
# Edit .env with your values

npm start
```

Server runs at `http://localhost:8788/mcp`.

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector@latest
# Open http://localhost:5173
# Enter server URL: http://localhost:8788/mcp
# Use OAuth flow to authenticate
```

## Production Deployment

### 1. Create a production GitHub OAuth App

- Homepage URL: `https://curlexai-mcp.<account>.workers.dev`
- Callback URL: `https://curlexai-mcp.<account>.workers.dev/callback`

### 2. Set secrets

```bash
npx wrangler secret put GITHUB_CLIENT_ID
npx wrangler secret put GITHUB_CLIENT_SECRET
npx wrangler secret put COOKIE_ENCRYPTION_KEY
npx wrangler secret put MIHWAR_ENDPOINT
npx wrangler secret put BAYYINAH_ENDPOINT
npx wrangler secret put AGENT_API_TOKEN
```

### 3. Create KV namespace

```bash
npx wrangler kv namespace create "OAUTH_KV"
# Update wrangler.jsonc with the returned KV namespace ID
```

### 4. Deploy

```bash
npx wrangler deploy
```

### 5. Connect from Claude Desktop

```json
{
  "mcpServers": {
    "curlexai": {
      "command": "npx",
      "args": ["mcp-remote", "https://curlexai-mcp.<account>.workers.dev/mcp"]
    }
  }
}
```

## Security

- GitHub OAuth 2.1 with CSRF protection and state binding
- `__Host-` cookie prefix prevents subdomain attacks on `*.workers.dev`
- HMAC-SHA256 signed approved-client cookies
- Modal endpoint URLs are server-side secrets, never exposed to MCP clients
- Content Security Policy headers on all HTML responses
- Input sanitization on all client-controlled content

## Boundary Compliance

This server is agent infrastructure under `.agents/mcp/` and complies with ADR-0001:
- Falls under "Agent operations" (allowed category 1)
- Modal URLs stay backend-only (enforced by `modal-boundary-gate.sh`)
- No product source, no public REST/GraphQL surface
- No `autoStart` flags
