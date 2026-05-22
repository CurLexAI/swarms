# MCP Server for CurLexAI Private Agents

This directory contains an MCP (Model Context Protocol) server that exposes the Modal-hosted **Mihwar** and **Bayyinah** agents as callable tools inside MCP-compatible clients (GitHub Copilot, Claude Desktop, Cursor, etc.).

---

## What It Does

The server speaks JSON-RPC over stdio and forwards tool calls to the Modal endpoints:

| Tool | Modal Endpoint | Model |
|------|----------------|-------|
| `mihwar_generate` | `MIHWAR_ENDPOINT` | DeepSeek-Coder-V2-Instruct |
| `bayyinah_review` | `BAYYINAH_ENDPOINT` | Qwen2.5-Coder-32B-Instruct |

No external dependencies required — uses only Python stdlib.

---

## GitHub Copilot Setup

Open the **MCP configuration** page in your repository's Copilot settings and paste:

```json
{
  "mcpServers": {
    "curlexai-agents": {
      "type": "local",
      "command": "python",
      "args": ["-u", ".agents/mcp/server.py"],
      "tools": ["mihwar_generate", "bayyinah_review"],
      "env": {
        "MIHWAR_ENDPOINT": "$MIHWAR_ENDPOINT",
        "BAYYINAH_ENDPOINT": "$BAYYINAH_ENDPOINT",
        "AGENT_API_TOKEN": "$AGENT_API_TOKEN"
      }
    }
  }
}
```

GitHub Copilot's schema requires:
- `"type": "local"` — spawn the server as a stdio subprocess.
- `"tools": [...]` — explicit allowlist of tool names the server provides.

The `$VAR` references resolve from the repository's `copilot environment` secrets.

---

## Render MCP Workspace Setup

This repository also includes a VS Code workspace MCP configuration at `.vscode/mcp.json`:

```json
{
  "servers": {
    "render": {
      "type": "http",
      "url": "https://mcp.render.com/mcp"
    }
  }
}
```

Use this for Render infrastructure operations from MCP-compatible clients that support workspace MCP configuration. It is intentionally separate from `curlexai-agents` because Render is a remote HTTP MCP server, while `curlexai-agents` is a local stdio server.

Security boundary:
- Do not hard-code Render credentials in this repository.
- Complete Render authorization in the MCP client/provider flow.
- Keep the local CurLexAI agent server and the remote Render server as distinct MCP entries.

---

## Claude Desktop / Cursor Setup

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or equivalent:

```json
{
  "mcpServers": {
    "curlexai-agents": {
      "command": "python",
      "args": ["-u", "/absolute/path/to/swarms/.agents/mcp/server.py"],
      "env": {
        "MIHWAR_ENDPOINT": "https://curlexai--mihwar-generate.modal.run",
        "BAYYINAH_ENDPOINT": "https://curlexai--bayyinah-review.modal.run",
        "AGENT_API_TOKEN": "your-token-here"
      }
    },
    "render": {
      "type": "http",
      "url": "https://mcp.render.com/mcp"
    }
  }
}
```

> Note: Claude Desktop / Cursor do **not** require the `"type"` field for local stdio servers — only GitHub Copilot does. Remote HTTP MCP servers may require a client-specific `type` field.

---

## Local Smoke Test

```bash
export MIHWAR_ENDPOINT="https://curlexai--mihwar-generate.modal.run"
export BAYYINAH_ENDPOINT="https://curlexai--bayyinah-review.modal.run"
export AGENT_API_TOKEN="your-token"

# List tools
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python .agents/mcp/server.py

# Call Bayyinah
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"bayyinah_review","arguments":{"code":"function add(a,b){return a+b}"}}}' \
  | python .agents/mcp/server.py
```

---

## Tool Schemas

### `mihwar_generate`

```json
{
  "task": "string (required)",
  "code": "string (optional)",
  "context": "string (optional)"
}
```

### `bayyinah_review`

```json
{
  "code": "string (required)",
  "context": "string (optional)"
}
```

---

## Security

- Tokens are read from environment variables; never logged or returned in errors.
- Modal endpoints are not exposed to the client — only the tool names appear.
- The server has no filesystem or shell access; it only forwards HTTPS POST requests.

---

## Why Not the Built-in `server-fetch`?

The community `@modelcontextprotocol/server-fetch` is generic and would require manual URL/auth handling per request. This dedicated server:

- Validates required environment variables on first call.
- Defines stable tool names (`mihwar_generate`, `bayyinah_review`) instead of raw URLs.
- Hides Modal endpoints from the client model entirely.
- Returns JSON-RPC errors mapped from network failures without leaking endpoint details.
