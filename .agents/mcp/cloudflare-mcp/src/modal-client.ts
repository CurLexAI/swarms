/**
 * Modal agent client adapted for Cloudflare Workers fetch runtime.
 * Proxies requests to Mihwar and Bayyinah Modal endpoints.
 * Modal URLs are never exposed to MCP clients — they stay server-side only.
 */

export interface AgentResult<T> {
  ok: true;
  value: T;
}

export interface AgentError {
  ok: false;
  error: { code: string; message: string };
}

export type Result<T> = AgentResult<T> | AgentError;

interface ModalClientConfig {
  mihwarEndpoint: string;
  bayyinahEndpoint: string;
  mihwarApiToken: string;
  bayyinahApiToken: string;
}

function agentError(message: string): AgentError {
  return { ok: false, error: { code: "AGENT_API_ERROR", message } };
}

async function postAgent<T>(
  endpoint: string,
  token: string,
  body: unknown,
): Promise<Result<T>> {
  if (!endpoint) {
    return agentError("Agent endpoint not configured");
  }

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return agentError(`Agent API returned ${response.status}`);
    }

    const payload = (await response.json()) as T;
    return { ok: true, value: payload };
  } catch {
    return agentError("Agent API request failed");
  }
}

export function mihwarGenerate(
  config: ModalClientConfig,
  task: string,
  code?: string,
  context?: string,
): Promise<Result<{ output: string }>> {
  return postAgent<{ output: string }>(
    config.mihwarEndpoint,
    config.mihwarApiToken,
    { task, code, context },
  );
}

export function bayyinahReview(
  config: ModalClientConfig,
  code: string,
  context?: string,
): Promise<Result<{ output: string }>> {
  return postAgent<{ output: string }>(
    config.bayyinahEndpoint,
    config.bayyinahApiToken,
    { code, context },
  );
}
