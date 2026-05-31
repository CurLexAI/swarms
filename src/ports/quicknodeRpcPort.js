export class QuicknodeIntegrationDisabledError extends Error {
    constructor() {
        super("Quicknode RPC integration is disabled. Configure QUICKNODE_ENABLED=true and QUICKNODE_RPC_URL in the secret store before use.");
        this.name = "QuicknodeIntegrationDisabledError";
    }
}
export class QuicknodeConfigurationError extends Error {
    constructor(message) {
        super(message);
        this.name = "QuicknodeConfigurationError";
    }
}
export class DisabledQuicknodeRpcPort {
    provider = "quicknode";
    enabled = false;
    async request(_request) {
        throw new QuicknodeIntegrationDisabledError();
    }
}
export function readQuicknodeConfig(env = process.env) {
    return {
        enabled: env.QUICKNODE_ENABLED === "true",
        rpcUrl: env.QUICKNODE_RPC_URL,
    };
}
export function sanitizeRpcUrl(rawUrl) {
    if (!rawUrl) {
        return "[UNCONFIGURED]";
    }
    let parsed;
    try {
        parsed = new URL(rawUrl);
    }
    catch {
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
export function assertQuicknodeConfigSafe(config) {
    if (!config.enabled) {
        return;
    }
    if (!config.rpcUrl) {
        throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL is required when QUICKNODE_ENABLED=true.");
    }
    let parsed;
    try {
        parsed = new URL(config.rpcUrl);
    }
    catch {
        throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL must be a valid URL.");
    }
    if (parsed.protocol !== "https:") {
        throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL must use HTTPS.");
    }
    if (parsed.username || parsed.password) {
        throw new QuicknodeConfigurationError("QUICKNODE_RPC_URL must not contain username or password credentials.");
    }
}
export function createQuicknodeRpcPort(config = readQuicknodeConfig(), logger) {
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
function looksSensitivePathSegment(segment) {
    return segment.length >= 16 && /[A-Za-z]/.test(segment) && /\d/.test(segment);
}
function looksSensitiveHost(hostname) {
    const firstLabel = hostname.split(".")[0] ?? "";
    return firstLabel.length >= 20 && /[A-Za-z]/.test(firstLabel) && /\d/.test(firstLabel);
}
