/**
 * OAuth utility functions with CSRF protection, state validation,
 * and approved-client cookie management.
 *
 * Security patterns:
 * - __Host- cookie prefix prevents subdomain attacks on *.workers.dev
 * - HMAC-SHA256 signed cookies for approved client lists
 * - SHA-256 hashed state binding to prevent CSRF in OAuth flow
 * - One-time-use state tokens stored in KV with TTL
 */

import type { AuthRequest, ClientInfo } from "@cloudflare/workers-oauth-provider";

export class OAuthError extends Error {
  constructor(
    public code: string,
    public description: string,
    public statusCode = 400,
  ) {
    super(description);
    this.name = "OAuthError";
  }

  toResponse(): Response {
    return new Response(
      JSON.stringify({ error: this.code, error_description: this.description }),
      { status: this.statusCode, headers: { "Content-Type": "application/json" } },
    );
  }
}

// --- CSRF Protection ---

export function generateCSRFProtection(): { token: string; setCookie: string } {
  const token = crypto.randomUUID();
  const setCookie = `__Host-CSRF_TOKEN=${token}; HttpOnly; Secure; Path=/; SameSite=Lax; Max-Age=600`;
  return { token, setCookie };
}

export function validateCSRFToken(
  formData: FormData,
  request: Request,
): { clearCookie: string } {
  const tokenFromForm = formData.get("csrf_token");
  if (!tokenFromForm || typeof tokenFromForm !== "string") {
    throw new OAuthError("invalid_request", "Missing CSRF token in form data");
  }

  const cookieHeader = request.headers.get("Cookie") || "";
  const cookies = cookieHeader.split(";").map((c) => c.trim());
  const csrfCookie = cookies.find((c) => c.startsWith("__Host-CSRF_TOKEN="));
  const tokenFromCookie = csrfCookie
    ? csrfCookie.substring("__Host-CSRF_TOKEN=".length)
    : null;

  if (!tokenFromCookie) {
    throw new OAuthError("invalid_request", "Missing CSRF token cookie");
  }

  if (tokenFromForm !== tokenFromCookie) {
    throw new OAuthError("invalid_request", "CSRF token mismatch");
  }

  return {
    clearCookie: "__Host-CSRF_TOKEN=; HttpOnly; Secure; Path=/; SameSite=Lax; Max-Age=0",
  };
}

// --- OAuth State Management ---

export async function createOAuthState(
  oauthReqInfo: AuthRequest,
  kv: KVNamespace,
  stateTTL = 600,
): Promise<{ stateToken: string }> {
  const stateToken = crypto.randomUUID();
  await kv.put(`oauth:state:${stateToken}`, JSON.stringify(oauthReqInfo), {
    expirationTtl: stateTTL,
  });
  return { stateToken };
}

export async function bindStateToSession(
  stateToken: string,
): Promise<{ setCookie: string }> {
  const encoder = new TextEncoder();
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoder.encode(stateToken));
  const hashHex = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  return {
    setCookie: `__Host-CONSENTED_STATE=${hashHex}; HttpOnly; Secure; Path=/; SameSite=Lax; Max-Age=600`,
  };
}

export async function validateOAuthState(
  request: Request,
  kv: KVNamespace,
): Promise<{ oauthReqInfo: AuthRequest; clearCookie: string }> {
  const url = new URL(request.url);
  const stateFromQuery = url.searchParams.get("state");

  if (!stateFromQuery) {
    throw new OAuthError("invalid_request", "Missing state parameter");
  }

  const storedDataJson = await kv.get(`oauth:state:${stateFromQuery}`);
  if (!storedDataJson) {
    throw new OAuthError("invalid_request", "Invalid or expired state");
  }

  const cookieHeader = request.headers.get("Cookie") || "";
  const cookies = cookieHeader.split(";").map((c) => c.trim());
  const consentedCookie = cookies.find((c) =>
    c.startsWith("__Host-CONSENTED_STATE="),
  );
  const consentedStateHash = consentedCookie
    ? consentedCookie.substring("__Host-CONSENTED_STATE=".length)
    : null;

  if (!consentedStateHash) {
    throw new OAuthError(
      "invalid_request",
      "Missing session binding cookie — authorization flow must be restarted",
    );
  }

  const encoder = new TextEncoder();
  const hashBuffer = await crypto.subtle.digest(
    "SHA-256",
    encoder.encode(stateFromQuery),
  );
  const stateHash = Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");

  if (stateHash !== consentedStateHash) {
    throw new OAuthError(
      "invalid_request",
      "State token does not match session — possible CSRF attack detected",
    );
  }

  let oauthReqInfo: AuthRequest;
  try {
    oauthReqInfo = JSON.parse(storedDataJson) as AuthRequest;
  } catch {
    throw new OAuthError("server_error", "Invalid state data", 500);
  }

  await kv.delete(`oauth:state:${stateFromQuery}`);

  return {
    oauthReqInfo,
    clearCookie:
      "__Host-CONSENTED_STATE=; HttpOnly; Secure; Path=/; SameSite=Lax; Max-Age=0",
  };
}

// --- Approved Clients ---

export async function isClientApproved(
  request: Request,
  clientId: string,
  cookieSecret: string,
): Promise<boolean> {
  const approved = await getApprovedClientsFromCookie(request, cookieSecret);
  return approved?.includes(clientId) ?? false;
}

export async function addApprovedClient(
  request: Request,
  clientId: string,
  cookieSecret: string,
): Promise<string> {
  const existing =
    (await getApprovedClientsFromCookie(request, cookieSecret)) || [];
  const updated = Array.from(new Set([...existing, clientId]));
  const payload = JSON.stringify(updated);
  const signature = await signData(payload, cookieSecret);
  const cookieValue = `${signature}.${btoa(payload)}`;
  return `__Host-APPROVED_CLIENTS=${cookieValue}; HttpOnly; Secure; Path=/; SameSite=Lax; Max-Age=2592000`;
}

// --- Approval Dialog Rendering ---

export function sanitizeText(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function sanitizeUrl(url: string): string {
  const normalized = url.trim();
  if (normalized.length === 0) return "";

  for (let i = 0; i < normalized.length; i++) {
    const code = normalized.charCodeAt(i);
    if ((code >= 0x00 && code <= 0x1f) || (code >= 0x7f && code <= 0x9f)) {
      return "";
    }
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(normalized);
  } catch {
    return "";
  }

  const scheme = parsedUrl.protocol.slice(0, -1).toLowerCase();
  if (!["https", "http"].includes(scheme)) return "";

  return normalized;
}

export interface ApprovalDialogOptions {
  client: ClientInfo | null;
  server: { name: string; logo?: string; description?: string };
  state: Record<string, unknown>;
  csrfToken: string;
  setCookie: string;
}

export function renderApprovalDialog(
  _request: Request,
  options: ApprovalDialogOptions,
): Response {
  const { client, server, state, csrfToken, setCookie } = options;
  const encodedState = btoa(JSON.stringify(state));
  const serverName = sanitizeText(server.name);
  const clientName = client?.clientName
    ? sanitizeText(client.clientName)
    : "Unknown MCP Client";
  const serverDescription = server.description
    ? sanitizeText(server.description)
    : "";
  const logoUrl = server.logo
    ? sanitizeText(sanitizeUrl(server.logo))
    : "";

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${clientName} | Authorization Request</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; color: #333; background: #f9fafb; margin: 0; padding: 0; }
    .container { max-width: 520px; margin: 3rem auto; padding: 1rem; }
    .card { background: #fff; border-radius: 12px; box-shadow: 0 8px 36px 8px rgba(0,0,0,0.08); padding: 2.5rem; }
    .header { display: flex; align-items: center; justify-content: center; gap: 1rem; margin-bottom: 1.5rem; }
    .logo { width: 48px; height: 48px; border-radius: 8px; object-fit: contain; }
    h1 { margin: 0; font-size: 1.25rem; font-weight: 500; }
    .desc { color: #555; text-align: center; margin-bottom: 1.5rem; }
    .alert { font-size: 1.1rem; text-align: center; margin: 1rem 0 1.5rem; }
    .info { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem; font-size: 0.9rem; color: #555; }
    .actions { display: flex; justify-content: flex-end; gap: 1rem; margin-top: 2rem; }
    .btn { padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 500; cursor: pointer; border: none; font-size: 1rem; }
    .btn-primary { background: #0070f3; color: #fff; }
    .btn-secondary { background: transparent; border: 1px solid #e5e7eb; color: #333; }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <div class="header">
        ${logoUrl ? `<img class="logo" src="${logoUrl}" alt="" />` : ""}
        <h1>${serverName}</h1>
      </div>
      ${serverDescription ? `<p class="desc">${serverDescription}</p>` : ""}
      <p class="alert"><strong>${clientName}</strong> is requesting access</p>
      <div class="info">
        This MCP client wants authorization on ${serverName}. If you approve, you will be redirected to GitHub to authenticate.
      </div>
      <form method="POST" action="/authorize">
        <input type="hidden" name="csrf_token" value="${csrfToken}" />
        <input type="hidden" name="state" value="${encodedState}" />
        <div class="actions">
          <button type="button" class="btn btn-secondary" onclick="window.close()">Cancel</button>
          <button type="submit" class="btn btn-primary">Approve</button>
        </div>
      </form>
    </div>
  </div>
</body>
</html>`;

  return new Response(html, {
    headers: {
      "Content-Security-Policy": "frame-ancestors 'none'",
      "Content-Type": "text/html; charset=utf-8",
      "Set-Cookie": setCookie,
      "X-Frame-Options": "DENY",
    },
  });
}

// --- Internal Helpers ---

async function getApprovedClientsFromCookie(
  request: Request,
  cookieSecret: string,
): Promise<string[] | null> {
  const cookieHeader = request.headers.get("Cookie");
  if (!cookieHeader) return null;

  const cookies = cookieHeader.split(";").map((c) => c.trim());
  const target = cookies.find((c) =>
    c.startsWith("__Host-APPROVED_CLIENTS="),
  );
  if (!target) return null;

  const cookieValue = target.substring("__Host-APPROVED_CLIENTS=".length);
  const parts = cookieValue.split(".");
  if (parts.length !== 2) return null;

  const [signatureHex, base64Payload] = parts;
  const payload = atob(base64Payload);
  const isValid = await verifySignature(signatureHex, payload, cookieSecret);
  if (!isValid) return null;

  try {
    const approvedClients = JSON.parse(payload);
    if (
      !Array.isArray(approvedClients) ||
      !approvedClients.every((item) => typeof item === "string")
    ) {
      return null;
    }
    return approvedClients as string[];
  } catch {
    return null;
  }
}

async function signData(data: string, secret: string): Promise<string> {
  const key = await importKey(secret);
  const enc = new TextEncoder();
  const signatureBuffer = await crypto.subtle.sign(
    "HMAC",
    key,
    enc.encode(data),
  );
  return Array.from(new Uint8Array(signatureBuffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function verifySignature(
  signatureHex: string,
  data: string,
  secret: string,
): Promise<boolean> {
  const key = await importKey(secret);
  const enc = new TextEncoder();
  try {
    const signatureBytes = new Uint8Array(
      signatureHex.match(/.{1,2}/g)!.map((byte) => Number.parseInt(byte, 16)),
    );
    return await crypto.subtle.verify(
      "HMAC",
      key,
      signatureBytes.buffer,
      enc.encode(data),
    );
  } catch {
    return false;
  }
}

async function importKey(secret: string): Promise<CryptoKey> {
  if (!secret) {
    throw new Error("cookieSecret is required for signing cookies");
  }
  const enc = new TextEncoder();
  return crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { hash: "SHA-256", name: "HMAC" },
    false,
    ["sign", "verify"],
  );
}
