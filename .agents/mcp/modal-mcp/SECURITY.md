# Security model for modal-mcp

## Trust boundary

- ChatGPT connects only to this MCP server.
- This MCP server connects to Modal API/endpoints.
- ChatGPT must **not** call Modal endpoints directly.

## Security controls in this scaffold

1. Bearer authentication required on `/sse`.
2. Strict TypeScript and typed `Result<T, E>` response pattern.
3. Mutating tools are disabled by default and require explicit approval flag.
4. No secret values are committed; only `.env.example` is provided.
5. Log retrieval is bounded by `MAX_LOG_LINES` to reduce exfiltration risk.

## Operator obligations

- Rotate `MCP_BEARER_TOKEN` periodically.
- Use least-privilege Modal token for read-only by default.
- Enable mutating tools only under change-control approval.
- Keep HTTPS termination enabled at the hosting edge (Cloudflare or Render).
