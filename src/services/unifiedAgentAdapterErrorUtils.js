const DEFAULT_MAX_ERROR_TEXT_LENGTH = 512;
const AUDIT_MAX_ERROR_TEXT_LENGTH = 160;

export const PYTHON_ENGINE_TRANSPORT_BLOCKER = "UNVERIFIED_RUNTIME";

const REDACTION_PATTERNS = [
  /(authorization["']?\s*[:=]\s*["']?bearer\s+)[^"'\s,}]+/gi,
  /((?:api[_-]?key|token|secret|password)["']?\s*[:=]\s*["']?)[^"'\s,}]+/gi
];

export function sanitizeBackendErrorText(rawText, maxLength = DEFAULT_MAX_ERROR_TEXT_LENGTH) {
  const normalized = typeof rawText === "string" ? rawText : String(rawText ?? "");
  let redacted = normalized;

  for (const pattern of REDACTION_PATTERNS) {
    redacted = redacted.replace(pattern, "$1[REDACTED]");
  }

  const truncated = redacted.length > maxLength;
  const snippet = truncated ? `${redacted.slice(0, maxLength)}…` : redacted;

  return {
    snippet,
    truncated,
    originalLength: normalized.length
  };
}

export function sanitizeBackendErrorForAudit(rawText) {
  return sanitizeBackendErrorText(rawText, AUDIT_MAX_ERROR_TEXT_LENGTH).snippet;
}

export function buildClientSafePythonEngineError(statusCode, correlationId) {
  const reference = correlationId ? ` (ref: ${correlationId})` : "";
  return `Python engine request failed with status ${statusCode}. Please try again later${reference}.`;
}
