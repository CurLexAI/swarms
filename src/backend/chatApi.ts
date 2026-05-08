export interface ChatApiConfig {
  environment: "prod" | "staging";
  allowedOrigins: {
    prod: string[];
    staging: string[];
  };
  allowCredentials: boolean;
}

export interface SimpleRequest {
  method: string;
  headers?: Record<string, string | undefined>;
}

export interface SimpleResponse {
  status: number;
  headers: Record<string, string>;
  body?: string;
}

function normalizeOrigin(origin: string | undefined): string | null {
  if (!origin) return null;
  try { return new URL(origin).origin; } catch { return null; }
}

function isOriginAllowed(origin: string | null, config: ChatApiConfig): boolean {
  if (!origin) return false;
  const allowlist = config.environment === "prod" ? config.allowedOrigins.prod : config.allowedOrigins.staging;
  return allowlist.includes(origin);
}

function buildCorsHeaders(req: SimpleRequest, config: ChatApiConfig): Record<string, string> {
  const origin = normalizeOrigin(req.headers?.origin ?? req.headers?.Origin);
  const originAllowed = isOriginAllowed(origin, config);

  const headers: Record<string, string> = {
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    Vary: "Origin",
  };

  if (originAllowed && origin) {
    headers["Access-Control-Allow-Origin"] = origin;
    if (config.allowCredentials) headers["Access-Control-Allow-Credentials"] = "true";
  }

  return headers;
}

export function handleChatApiRequest(req: SimpleRequest, config: ChatApiConfig): SimpleResponse {
  const corsHeaders = buildCorsHeaders(req, config);
  const origin = normalizeOrigin(req.headers?.origin ?? req.headers?.Origin);
  const originAllowed = isOriginAllowed(origin, config);

  if (req.method === "OPTIONS") return { status: 204, headers: corsHeaders };

  if (req.method !== "POST") {
    return { status: 405, headers: { ...corsHeaders, Allow: "POST, OPTIONS" }, body: "Method Not Allowed" };
  }

  if (!originAllowed) return { status: 403, headers: corsHeaders, body: "Origin Not Allowed" };

  return { status: 200, headers: corsHeaders, body: "ok" };
}

export function loadChatApiConfigFromEnv(env: NodeJS.ProcessEnv): ChatApiConfig {
  const environment = env.APP_ENV === "prod" ? "prod" : "staging";
  const prod = (env.CORS_ALLOWED_ORIGINS_PROD ?? "").split(",").map((v) => v.trim()).filter(Boolean);
  const staging = (env.CORS_ALLOWED_ORIGINS_STAGING ?? "").split(",").map((v) => v.trim()).filter(Boolean);
  const allowCredentials = env.CORS_ALLOW_CREDENTIALS === "true";
  return { environment, allowedOrigins: { prod, staging }, allowCredentials };
}
