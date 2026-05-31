export type JsonRpcParams = readonly unknown[] | Record<string, unknown>;

export interface JsonRpcRequest {
  readonly method: string;
  readonly params?: JsonRpcParams;
}

export interface JsonRpcResponse<T = unknown> {
  readonly result: T;
}

export interface Web3RpcPort {
  readonly provider: "quicknode";
  readonly enabled: boolean;
  request<T = unknown>(request: JsonRpcRequest): Promise<JsonRpcResponse<T>>;
}

export interface QuicknodePortConfig {
  readonly enabled: boolean;
  readonly rpcUrl?: string;
}

export interface QuicknodePortLogger {
  warn(message: string, metadata?: Record<string, unknown>): void;
  info?(message: string, metadata?: Record<string, unknown>): void;
}

export class QuicknodeIntegrationDisabledError extends Error {
  constructor() {
    super("Quicknode RPC integration is disabled. Configure QUICKNODE_ENABLED=true and QUICKNODE_RPC_URL in the secret store before use.");
    this.name = "QuicknodeIntegrationDisabledError";
  }
}

export class QuicknodeConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "QuicknodeConfigurationError";
  }
}

export class DisabledQuicknodeRpcPort implements Web3RpcPort {
  readonly provider = "quicknode" as const;
  readonly enabled = false;

  async request<T = unknown>(_request: JsonRpcRequest): Promise<JsonRpcResponse<T>> {
    throw new QuicknodeIntegrationDisabledError();
  }
}

export function readQuicknodeConfig(env: NodeJS.ProcessEnv = process.env): QuicknodePortConfig {
  return {
    enabled: env.QUICKNODE_ENABLED === "true",
    rpcUrl: env.QUICKNODE_RPC_URL,
  };
}

export function sanitizeRpcUrl(rawUrl: string | undefined): string {
  if (!rawUrl) {
    return "[UNCONFIGURED]";
  }

  let parsed: URL;
  try {
    parsed = new URL(rawUrl);
  } catch {
    return "[INVALID_URL_REDACTED]";
  }

  parsed.username = parsed.username ? "[REDACTED]" : "";
  parsed.password = parsed.password ? "[REDACTED]" : "";

  const redactedSearch = new URLSearchParams();
  for (const key of parsed.searchParams.keys()) {
    redactedSearch.set(key, "[REDACTED]");
  }
  parsed.search = redactedSearch.toString();

  const pathParts = parsed.pathname
    .split("/")
    .map((part) => (looksSensitivePathSegment(part) ? "[REDACTED]" : part));
  parsed.pathname = pathParts.join("/");

  if (looksSensitiveHost(parsed.hostname)) {
    parsed.hostname = "redacted.invalid";
  }

  return parsed.toString();
}

export function assertQuicknodeConfigSafe(config: QuicknodePortConfig): void {
  if (!config.enabled) {
    return;
  }

  if (!config.rpcUrl) {
    throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL is required when QUICKNODE_ENABLED=true.");
  }

  let parsed: URL;
  try {
    parsed = new URL(config.rpcUrl);
  } catch {
    throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL must be a valid URL.");
  }

  if (parsed.protocol !== "https:") {
    throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL must use HTTPS.");
  }

  if (parsed.username || parsed.password) {
    throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL must not contain username or password credentials.");
  }
}

export function createQuicknodeRpcPort(
  config: QuicknodePortConfig = readQuicknodeConfig(),
  logger?: QuicknodePortLogger,
): Web3RpcPort {
  if (!config.enabled) {
    logger?.info?.("Quicknode RPC integration disabled", { provider: "quicknode" });
    return new DisabledQuicknodeRpcPort();
  }

  assertQuicknodeConfigSafe(config);
  logger?.warn("Quicknode RPC integration requested but no live adapter is registered", {
    provider: "quicknode",
    rpcUrl: sanitizeRpcUrl(config.rpcUrl),
  });
  return new DisabledQuicknodeRpcPort();
}

function looksSensitivePathSegment(segment: string): boolean {
  return segment.length >= 16 && /[A-Za-z]/.test(segment) && /\d/.test(segment);
}

function looksSensitiveHost(hostname: string): boolean {
  const firstLabel = hostname.split(".")[0] ?? "";
  return firstLabel.length >= 20 && /[A-Za-z]/.test(firstLabel) && /\d/.test(firstLabel);
}
