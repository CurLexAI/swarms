// Qal'a (قلعة) — Q7 Sealed Audit Sink
//
// Append-only, tamper-evident JSONL log adapter. Each record carries
// a chained SHA-256 hash so any later tampering with prior records
// invalidates the chain.
//
// No external persistence. No background workers. No network calls.
// Payloads MUST be sanitized by the caller (Q5 KSA-PII + existing
// audit redaction) before being passed to append(); this module does
// not redact — that responsibility stays with the caller so the gate
// pipeline remains explicit.
//
// See docs/decisions/ADR-0003-qala-security-architecture.md §Q7.

import { createHash, randomUUID } from "node:crypto";
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
} from "node:fs";
import { dirname, resolve } from "node:path";

export const QALA_GENESIS_HASH = "GENESIS";

export type QalaAuditEvent =
  | "input_validation_blocked"
  | "input_validation_request_changes"
  | "input_validation_approved"
  | "output_validation_blocked"
  | "output_validation_request_changes"
  | "output_validation_approved"
  | "ksa_pii_detected"
  | "policy_decision"
  | "egress_check_blocked"
  | "egress_check_approved"
  | "auth_check_blocked"
  | "auth_check_approved"
  // Qarar router decisions (audited via build_audited_execution_plan).
  | "classification_decision"
  | "route_decision"
  | "route_blocked";

const QALA_AUDIT_EVENTS: ReadonlySet<QalaAuditEvent> = new Set([
  "input_validation_blocked",
  "input_validation_request_changes",
  "input_validation_approved",
  "output_validation_blocked",
  "output_validation_request_changes",
  "output_validation_approved",
  "ksa_pii_detected",
  "policy_decision",
  "egress_check_blocked",
  "egress_check_approved",
  "auth_check_blocked",
  "auth_check_approved",
  // Qarar router decisions (audited via build_audited_execution_plan).
  "classification_decision",
  "route_decision",
  "route_blocked",
]);

export interface QalaAuditAppendInput {
  readonly event: QalaAuditEvent;
  readonly traceId: string;
  readonly spanId: string;
  readonly tenantId: string;
  readonly occurredAt?: string;
  readonly payload?: Readonly<Record<string, unknown>>;
}

export interface QalaAuditRecord {
  readonly recordId: string;
  readonly prevHash: string;
  readonly recordHash: string;
  readonly event: QalaAuditEvent;
  readonly traceId: string;
  readonly spanId: string;
  readonly tenantId: string;
  readonly occurredAt: string;
  readonly payload: Readonly<Record<string, unknown>>;
}

export type QalaAuditAppendError =
  | "AUDIT_WRITE_FAILED"
  | "AUDIT_INVALID_EVENT"
  | "AUDIT_INVALID_INPUT";

export type QalaAuditAppendResult =
  | { readonly ok: true; readonly value: QalaAuditRecord }
  | {
      readonly ok: false;
      readonly error: QalaAuditAppendError;
      readonly message: string;
    };

export type QalaAuditVerifyResult =
  | { readonly ok: true; readonly recordsVerified: number }
  | {
      readonly ok: false;
      readonly error: "AUDIT_CHAIN_BROKEN" | "AUDIT_READ_FAILED";
      readonly message: string;
      readonly atRecord?: number;
    };

function sha256(input: string): string {
  return createHash("sha256").update(input, "utf8").digest("hex");
}

function defaultSinkPath(): string {
  // Resolved at sink-construction time; under artifacts/security/ which
  // is gitignored by convention (matches sovereignCyberRadar.EvidenceLedger).
  return process.env.QALA_AUDIT_SINK_PATH ?? "artifacts/security/qala-audit.jsonl";
}

function isQalaAuditEvent(value: unknown): value is QalaAuditEvent {
  return (
    typeof value === "string" && QALA_AUDIT_EVENTS.has(value as QalaAuditEvent)
  );
}

function sortKeysRecursive(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sortKeysRecursive(item));
  }
  if (value !== null && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      out[key] = sortKeysRecursive((value as Record<string, unknown>)[key]);
    }
    return out;
  }
  return value;
}

function canonicalize(input: QalaAuditAppendInput, occurredAt: string): string {
  // Deterministic, recursively key-sorted JSON so the hash is
  // reproducible regardless of insertion order at any depth.
  // Mirrors Python's json.dumps(..., sort_keys=True).
  const obj = sortKeysRecursive({
    event: input.event,
    occurredAt,
    payload: input.payload ?? {},
    spanId: input.spanId,
    tenantId: input.tenantId,
    traceId: input.traceId,
  });
  return JSON.stringify(obj);
}

export class QalaAuditSink {
  private readonly path: string;

  public constructor(sinkPath?: string) {
    this.path = resolve(sinkPath ?? defaultSinkPath());
    const dir = dirname(this.path);
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
    }
  }

  public get sinkPath(): string {
    return this.path;
  }

  public append(input: QalaAuditAppendInput): QalaAuditAppendResult {
    if (!isQalaAuditEvent(input.event)) {
      return {
        ok: false,
        error: "AUDIT_INVALID_EVENT",
        message: `unknown event: ${String(input.event)}`,
      };
    }
    if (
      typeof input.traceId !== "string" ||
      typeof input.spanId !== "string" ||
      typeof input.tenantId !== "string" ||
      input.traceId.length === 0 ||
      input.spanId.length === 0 ||
      input.tenantId.length === 0
    ) {
      return {
        ok: false,
        error: "AUDIT_INVALID_INPUT",
        message: "trace_id, span_id, and tenant_id are required",
      };
    }

    const occurredAt = input.occurredAt ?? new Date().toISOString();
    const prevHash = this.readLastHash();
    const canonical = canonicalize(input, occurredAt);
    const recordHash = sha256(`${prevHash}\n${canonical}`);

    const record: QalaAuditRecord = {
      recordId: randomUUID(),
      prevHash,
      recordHash,
      event: input.event,
      traceId: input.traceId,
      spanId: input.spanId,
      tenantId: input.tenantId,
      occurredAt,
      payload: input.payload ?? {},
    };

    try {
      appendFileSync(this.path, `${JSON.stringify(record)}\n`, {
        encoding: "utf8",
      });
      return { ok: true, value: record };
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "unknown audit write error";
      return { ok: false, error: "AUDIT_WRITE_FAILED", message };
    }
  }

  public verifyChain(): QalaAuditVerifyResult {
    if (!existsSync(this.path)) {
      return { ok: true, recordsVerified: 0 };
    }
    let content: string;
    try {
      content = readFileSync(this.path, "utf8");
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "unknown audit read error";
      return { ok: false, error: "AUDIT_READ_FAILED", message };
    }

    const lines = content.split("\n").filter((line) => line.length > 0);
    let expectedPrev = QALA_GENESIS_HASH;
    let index = 0;
    for (const line of lines) {
      let parsed: QalaAuditRecord;
      try {
        parsed = JSON.parse(line) as QalaAuditRecord;
      } catch {
        return {
          ok: false,
          error: "AUDIT_CHAIN_BROKEN",
          message: "record is not valid JSON",
          atRecord: index,
        };
      }

      if (parsed.prevHash !== expectedPrev) {
        return {
          ok: false,
          error: "AUDIT_CHAIN_BROKEN",
          message: `prev_hash mismatch at record ${index}`,
          atRecord: index,
        };
      }

      const canonical = canonicalize(
        {
          event: parsed.event,
          traceId: parsed.traceId,
          spanId: parsed.spanId,
          tenantId: parsed.tenantId,
          payload: parsed.payload,
        },
        parsed.occurredAt,
      );
      const recomputed = sha256(`${expectedPrev}\n${canonical}`);
      if (recomputed !== parsed.recordHash) {
        return {
          ok: false,
          error: "AUDIT_CHAIN_BROKEN",
          message: `record_hash mismatch at record ${index}`,
          atRecord: index,
        };
      }
      expectedPrev = parsed.recordHash;
      index += 1;
    }

    return { ok: true, recordsVerified: index };
  }

  private readLastHash(): string {
    if (!existsSync(this.path)) return QALA_GENESIS_HASH;
    const content = readFileSync(this.path, "utf8").trim();
    if (content.length === 0) return QALA_GENESIS_HASH;
    const lines = content.split("\n").filter((line) => line.length > 0);
    const last = lines[lines.length - 1];
    if (last === undefined) return QALA_GENESIS_HASH;
    try {
      const parsed = JSON.parse(last) as { recordHash?: unknown };
      return typeof parsed.recordHash === "string"
        ? parsed.recordHash
        : QALA_GENESIS_HASH;
    } catch {
      return QALA_GENESIS_HASH;
    }
  }
}
