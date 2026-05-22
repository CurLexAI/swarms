/**
 * CurLexAI Remote MCP Server — Cloudflare Workers entry point.
 *
 * Exposes Mihwar and Bayyinah agent tools via the Model Context Protocol
 * with GitHub OAuth authentication. Deployed as a Cloudflare Worker with
 * Durable Objects (for MCP session state) and KV (for OAuth state).
 *
 * Architecture:
 *   MCP Client → (OAuth) → this Worker → (bearer token) → Modal agents
 *
 * Modal endpoint URLs are backend secrets — never sent to MCP clients.
 */

import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { AgentMCP } from "./mcp-agent";
import { GitHubHandler } from "./github-handler";

export default new OAuthProvider({
  apiHandler: AgentMCP.serve("/mcp"),
  apiRoute: "/mcp",
  authorizeEndpoint: "/authorize",
  clientRegistrationEndpoint: "/register",
  defaultHandler: GitHubHandler as any,
  tokenEndpoint: "/token",
});

export { AgentMCP };
