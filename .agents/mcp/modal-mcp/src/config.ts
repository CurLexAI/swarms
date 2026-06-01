import { Result } from './types.js';

export interface Config {
  mcpBaseUrl: string;
  mcpBearerToken: string;
  modalApiToken: string;
  modalApiBaseUrl: string;
  enableMutatingTools: boolean;
  deploymentAllowlist: string[];
  maxLogLines: number;
  mihwarEndpoint: string | undefined;
  bayyinahEndpoint: string | undefined;
  agentApiToken: string | undefined;
}

export function loadConfig(env: NodeJS.ProcessEnv): Result<Config, string> {
  const required = ['MCP_BASE_URL', 'MCP_BEARER_TOKEN', 'MODAL_API_TOKEN', 'MODAL_API_BASE_URL'] as const;
  for (const key of required) {
    if (!env[key] || env[key]?.trim() === '') {
      return { ok: false, error: `Missing required env: ${key}` };
    }
  }

  const max = Number(env.MAX_LOG_LINES ?? '200');
  if (!Number.isInteger(max) || max <= 0) {
    return { ok: false, error: 'MAX_LOG_LINES must be a positive integer' };
  }

  return {
    ok: true,
    value: {
      mcpBaseUrl: env.MCP_BASE_URL as string,
      mcpBearerToken: env.MCP_BEARER_TOKEN as string,
      modalApiToken: env.MODAL_API_TOKEN as string,
      modalApiBaseUrl: env.MODAL_API_BASE_URL as string,
      enableMutatingTools: (env.ENABLE_MUTATING_TOOLS ?? 'false').toLowerCase() === 'true',
      deploymentAllowlist: (env.MODAL_DEPLOYMENT_ALLOWLIST ?? '')
        .split(',')
        .map((v) => v.trim())
        .filter((v) => v.length > 0),
      maxLogLines: max,
      mihwarEndpoint: env.MIHWAR_ENDPOINT,
      bayyinahEndpoint: env.BAYYINAH_ENDPOINT,
      agentApiToken: env.AGENT_API_TOKEN
    }
  };
}
