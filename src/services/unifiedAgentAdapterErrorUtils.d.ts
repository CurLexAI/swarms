export const PYTHON_ENGINE_TRANSPORT_BLOCKER: "UNVERIFIED_RUNTIME";

export interface SanitizedBackendError {
  snippet: string;
  truncated: boolean;
  originalLength: number;
}

export function sanitizeBackendErrorText(rawText: unknown, maxLength?: number): SanitizedBackendError;
export function sanitizeBackendErrorForAudit(rawText: unknown): string;
export function buildClientSafePythonEngineError(statusCode: number | string, correlationId?: string): string;
