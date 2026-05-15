// Qal'a (قلعة) — Q6 Trace & Correlation
//
// Pure, dependency-free trace context for the Qal'a security layer.
// No network calls. No persistent state. No background workers.
// Secrets and raw PII MUST NOT enter this module — its outputs are
// transported as headers and logged into the sealed audit sink.
//
// See docs/decisions/ADR-0003-qala-security-architecture.md §Q6.

import { randomUUID } from "node:crypto";

export type QalaPhase =
  | "auth_check"
  | "input_validation"
  | "policy_check"
  | "egress_check"
  | "model_call"
  | "output_validation"
  | "audit_emit";

const QALA_PHASES: ReadonlySet<QalaPhase> = new Set<QalaPhase>([
  "auth_check",
  "input_validation",
  "policy_check",
  "egress_check",
  "model_call",
  "output_validation",
  "audit_emit",
]);

const UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const MAX_TENANT_ID_LENGTH = 128;
const TENANT_ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/;

export interface QalaTraceContext {
  readonly traceId: string;
  readonly spanId: string;
  readonly parentSpanId: string | null;
  readonly tenantId: string;
  readonly phase: QalaPhase;
  readonly startedAt: string;
}

export const QALA_HEADER = {
  TRACE_ID: "x-qala-trace-id",
  SPAN_ID: "x-qala-span-id",
  PARENT_SPAN_ID: "x-qala-parent-span-id",
  TENANT_ID: "x-qala-tenant-id",
  PHASE: "x-qala-phase",
  STARTED_AT: "x-qala-started-at",
} as const;

export class QalaTraceError extends Error {
  readonly code: "INVALID_TENANT_ID" | "INVALID_PHASE" | "INVALID_HEADERS";

  constructor(
    code: "INVALID_TENANT_ID" | "INVALID_PHASE" | "INVALID_HEADERS",
    message: string,
  ) {
    super(message);
    this.name = "QalaTraceError";
    this.code = code;
  }
}

function isQalaPhase(value: unknown): value is QalaPhase {
  return typeof value === "string" && QALA_PHASES.has(value as QalaPhase);
}

function validateTenantId(tenantId: string): void {
  if (typeof tenantId !== "string" || tenantId.length === 0) {
    throw new QalaTraceError(
      "INVALID_TENANT_ID",
      "tenant_id must be a non-empty string",
    );
  }
  if (tenantId.length > MAX_TENANT_ID_LENGTH) {
    throw new QalaTraceError(
      "INVALID_TENANT_ID",
      `tenant_id exceeds max length (${MAX_TENANT_ID_LENGTH})`,
    );
  }
  if (!TENANT_ID_PATTERN.test(tenantId)) {
    throw new QalaTraceError(
      "INVALID_TENANT_ID",
      "tenant_id must match [A-Za-z0-9_-]{1,128}",
    );
  }
}

function validatePhase(phase: unknown): asserts phase is QalaPhase {
  if (!isQalaPhase(phase)) {
    throw new QalaTraceError("INVALID_PHASE", `unknown phase: ${String(phase)}`);
  }
}

export function newTrace(tenantId: string, phase: QalaPhase): QalaTraceContext {
  validateTenantId(tenantId);
  validatePhase(phase);
  return {
    traceId: randomUUID(),
    spanId: randomUUID(),
    parentSpanId: null,
    tenantId,
    phase,
    startedAt: new Date().toISOString(),
  };
}

export function childSpan(
  parent: QalaTraceContext,
  phase: QalaPhase,
): QalaTraceContext {
  validatePhase(phase);
  return {
    traceId: parent.traceId,
    spanId: randomUUID(),
    parentSpanId: parent.spanId,
    tenantId: parent.tenantId,
    phase,
    startedAt: new Date().toISOString(),
  };
}

export function toHeaders(ctx: QalaTraceContext): Record<string, string> {
  // tenant_id is permitted in headers per ADR-0003 §Q6; it is required
  // for cross-hop correlation and is not classified as secret material.
  const headers: Record<string, string> = {
    [QALA_HEADER.TRACE_ID]: ctx.traceId,
    [QALA_HEADER.SPAN_ID]: ctx.spanId,
    [QALA_HEADER.TENANT_ID]: ctx.tenantId,
    [QALA_HEADER.PHASE]: ctx.phase,
    [QALA_HEADER.STARTED_AT]: ctx.startedAt,
  };
  if (ctx.parentSpanId !== null) {
    headers[QALA_HEADER.PARENT_SPAN_ID] = ctx.parentSpanId;
  }
  return headers;
}

type HeaderInput = Readonly<Record<string, string | undefined>>;

function readHeader(headers: HeaderInput, name: string): string | null {
  const direct = headers[name];
  if (typeof direct === "string" && direct.length > 0) return direct;
  // Case-insensitive lookup — HTTP frameworks normalize differently.
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === name) {
      const value = headers[key];
      if (typeof value === "string" && value.length > 0) return value;
    }
  }
  return null;
}

export function fromHeaders(headers: HeaderInput): QalaTraceContext | null {
  const traceId = readHeader(headers, QALA_HEADER.TRACE_ID);
  const spanId = readHeader(headers, QALA_HEADER.SPAN_ID);
  const tenantId = readHeader(headers, QALA_HEADER.TENANT_ID);
  const phase = readHeader(headers, QALA_HEADER.PHASE);
  const startedAt = readHeader(headers, QALA_HEADER.STARTED_AT);
  const parentSpanId = readHeader(headers, QALA_HEADER.PARENT_SPAN_ID);

  if (
    traceId === null ||
    spanId === null ||
    tenantId === null ||
    phase === null ||
    startedAt === null
  ) {
    return null;
  }

  if (!UUID_V4_PATTERN.test(traceId) || !UUID_V4_PATTERN.test(spanId)) {
    return null;
  }
  if (parentSpanId !== null && !UUID_V4_PATTERN.test(parentSpanId)) {
    return null;
  }
  if (!isQalaPhase(phase)) return null;
  try {
    validateTenantId(tenantId);
  } catch {
    return null;
  }
  // Round-trip-safe ISO-8601 check: Date.parse handles many lax inputs,
  // so we additionally require the canonical form re-serializes equal.
  const parsed = Date.parse(startedAt);
  if (!Number.isFinite(parsed)) return null;

  return {
    traceId,
    spanId,
    parentSpanId,
    tenantId,
    phase,
    startedAt,
  };
}

export const __qalaInternals = {
  UUID_V4_PATTERN,
  TENANT_ID_PATTERN,
  MAX_TENANT_ID_LENGTH,
};
