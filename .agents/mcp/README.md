# MCP Server for CurLexAI Private Agents

This directory contains MCP (Model Context Protocol) servers that expose the Modal-hosted **Mihwar** and **Bayyinah** agents as callable tools inside MCP-compatible clients.

**Two deployment models:**
1. **Local** (`.agents/mcp/server.py`) — Python stdio server for GitHub Copilot, Claude Desktop, Cursor
2. **Remote** (`.agents/mcp/modal-mcp/`) — Node.js HTTPS server on Render for ChatGPT, Claude web, and other remote clients

See [RENDER_MCP_INTEGRATION.md](./RENDER_MCP_INTEGRATION.md) for remote deployment instructions.

This repository also includes `.vscode/mcp.json` for connecting MCP-compatible workspace clients directly to Render's hosted MCP endpoint at `https://mcp.render.com/mcp`.

---

## What It Does

The server speaks JSON-RPC over stdio and forwards tool calls to the Modal endpoints:

| Tool | Modal Endpoint | Model |
|------|----------------|-------|
| `mihwar_generate` | `MIHWAR_ENDPOINT` | DeepSeek-Coder-V2-Instruct |
| `bayyinah_review` | `BAYYINAH_ENDPOINT` | Qwen2.5-Coder-32B-Instruct |
| `free_birds_review` | `BAYYINAH_ENDPOINT` | Qwen2.5-Coder-32B-Instruct |
| `free_birds_design` | `MIHWAR_ENDPOINT` | DeepSeek-Coder-V2-Instruct |

No external dependencies required — uses only Python stdlib.

> **Identity note.** The tools above are MCP-exposed surfaces, consumable by any MCP client (GitHub Copilot, Claude Desktop, Cursor, Continue, direct stdio peers). "Copilot" is the UI label of one such client, not a distinct runtime — every client hits the same JSON-RPC server and reaches the same Modal endpoints. The per-client setup sections below differ only in how each host spawns the stdio process and reads env vars.

---

## Aegis Gateway Controls

The local stdio server includes the first Aegis MCP gateway layer:

- `tools/list` is filtered by caller role.
- `tools/call` is denied before Modal dispatch when the role cannot use the requested tool.
- Tool-call arguments are inspected for prompt-injection style abuse, such as instruction override, hidden prompt disclosure, safety bypass, jailbreak persona, or secret-exfiltration requests.
- Discovery and call decisions are written to the Qal'a sealed audit sink as sanitized `policy_decision` records. Raw tool arguments are never written; the audit payload records argument keys, byte length, SHA-256 hash, decision reason, and rule ids.

Roles can be supplied through MCP request metadata:

```json
{
  "_meta": {
    "aegis": {
      "role": "observer"
    }
  }
}
```

If request metadata is absent, `AEGIS_MCP_ROLE` is used. Unknown roles degrade to `observer`.

| Role | Discoverable/callable tools |
|------|-----------------------------|
| `observer` | `bayyinah_review`, `free_birds_review` |
| `reviewer` | `bayyinah_review`, `free_birds_review` |
| `architect` | all CurLexAI agent tools |
| `operator` | all CurLexAI agent tools |
| `admin` | all CurLexAI agent tools |

Optional environment variables:

```text
AEGIS_MCP_ROLE=operator
AEGIS_TENANT_ID=system
QALA_AUDIT_SINK_PATH=artifacts/security/qala-audit.jsonl
```

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
      "tools": ["mihwar_generate", "bayyinah_review", "free_birds_review", "free_birds_design"],
      "env": {
        "MIHWAR_ENDPOINT": "$MIHWAR_ENDPOINT",
        "BAYYINAH_ENDPOINT": "$BAYYINAH_ENDPOINT",
        "AGENT_API_TOKEN": "$AGENT_API_TOKEN",
        "AEGIS_MCP_ROLE": "$AEGIS_MCP_ROLE",
        "AEGIS_TENANT_ID": "$AEGIS_TENANT_ID"
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

`.vscode/mcp.json` defines Render as a remote HTTP MCP server:

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
        "AGENT_API_TOKEN": "your-token-here",
        "AEGIS_MCP_ROLE": "operator",
        "AEGIS_TENANT_ID": "system"
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
export AEGIS_MCP_ROLE="operator"

# List tools
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{"_meta":{"aegis":{"role":"observer"}}}}' \
  | python .agents/mcp/server.py

# Call Bayyinah
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"bayyinah_review","arguments":{"code":"function add(a,b){return a+b}"},"_meta":{"aegis":{"role":"reviewer"}}}}' \
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
- The server has no filesystem or shell access for tools; it only forwards HTTPS POST requests after Aegis authorization.
- Aegis audit records are sanitized and contain no raw tool-call input.

---

## Why Not the Built-in `server-fetch`?

The community `@modelcontextprotocol/server-fetch` is generic and would require manual URL/auth handling per request. This dedicated server:

- Validates required environment variables on first call.
- Defines stable tool names (`mihwar_generate`, `bayyinah_review`) instead of raw URLs.
- Hides Modal endpoints from the client model entirely.
- Returns JSON-RPC errors mapped from network failures without leaking endpoint details.
- Adds Aegis role filtering, prompt-injection inspection, and Qal'a audit records at the MCP boundary.
