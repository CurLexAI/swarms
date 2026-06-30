import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  QALA_GENESIS_HASH,
  QalaAuditSink,
} from "../src/security/qalaAuditSink.js";

function withTempSink(fn) {
  const dir = mkdtempSync(join(tmpdir(), "qala-audit-"));
  try {
    fn(new QalaAuditSink(join(dir, "audit.jsonl")));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function validAppend(sink, overrides = {}) {
  return sink.append({
    event: "input_validation_approved",
    traceId: "trace-id-1",
    spanId: "span-id-1",
    tenantId: "tenant-A",
    payload: { k: "v" },
    ...overrides,
  });
}

test("first record chains from GENESIS", () => {
  withTempSink((sink) => {
    const result = validAppend(sink);
    assert.equal(result.ok, true);
    assert.equal(result.value.prevHash, QALA_GENESIS_HASH);
    assert.equal(result.value.recordHash.length, 64);
  });
});

test("subsequent records chain correctly", () => {
  withTempSink((sink) => {
    const a = validAppend(sink, { payload: { i: 1 } });
    const b = validAppend(sink, { payload: { i: 2 } });
    const c = validAppend(sink, { payload: { i: 3 } });
    assert.equal(b.value.prevHash, a.value.recordHash);
    assert.equal(c.value.prevHash, b.value.recordHash);
  });
});

test("verifyChain passes for a clean log", () => {
  withTempSink((sink) => {
    validAppend(sink);
    validAppend(sink);
    validAppend(sink);
    const result = sink.verifyChain();
    assert.equal(result.ok, true);
    assert.equal(result.recordsVerified, 3);
  });
});

test("modifying a payload breaks the chain", () => {
  withTempSink((sink) => {
    validAppend(sink, { payload: { i: 1 } });
    validAppend(sink, { payload: { i: 2 } });
    const lines = readFileSync(sink.sinkPath, "utf8").trim().split("\n");
    const first = JSON.parse(lines[0]);
    first.payload.i = 99;
    lines[0] = JSON.stringify(first);
    writeFileSync(sink.sinkPath, lines.join("\n") + "\n");
    const result = sink.verifyChain();
    assert.equal(result.ok, false);
    assert.equal(result.error, "AUDIT_CHAIN_BROKEN");
    assert.equal(result.atRecord, 0);
  });
});

test("modifying prev_hash breaks the chain", () => {
  withTempSink((sink) => {
    validAppend(sink);
    validAppend(sink);
    const lines = readFileSync(sink.sinkPath, "utf8").trim().split("\n");
    const second = JSON.parse(lines[1]);
    second.prevHash = "0".repeat(64);
    lines[1] = JSON.stringify(second);
    writeFileSync(sink.sinkPath, lines.join("\n") + "\n");
    const result = sink.verifyChain();
    assert.equal(result.ok, false);
    assert.equal(result.atRecord, 1);
  });
});

test("rejects unknown event", () => {
  withTempSink((sink) => {
    const result = sink.append({
      event: "garbage",
      traceId: "t",
      spanId: "s",
      tenantId: "x",
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "AUDIT_INVALID_EVENT");
  });
});

test("rejects missing trace id", () => {
  withTempSink((sink) => {
    const result = sink.append({
      event: "input_validation_approved",
      traceId: "",
      spanId: "s",
      tenantId: "x",
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "AUDIT_INVALID_INPUT");
  });
});

test("rejects missing tenant", () => {
  withTempSink((sink) => {
    const result = sink.append({
      event: "input_validation_approved",
      traceId: "t",
      spanId: "s",
      tenantId: "",
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "AUDIT_INVALID_INPUT");
  });
});

test("payload defaults to empty object", () => {
  withTempSink((sink) => {
    const result = sink.append({
      event: "input_validation_approved",
      traceId: "t",
      spanId: "s",
      tenantId: "x",
    });
    assert.equal(result.ok, true);
    assert.deepEqual(result.value.payload, {});
  });
});

test("append-only API has no update / delete", () => {
  withTempSink((sink) => {
    assert.equal(typeof sink.update, "undefined");
    assert.equal(typeof sink.modify, "undefined");
    assert.equal(typeof sink.delete, "undefined");
    assert.equal(typeof sink.remove, "undefined");
  });
});

test("payload key order does not change the hash", () => {
  withTempSink((sinkA) => {
    withTempSink((sinkB) => {
      const a = sinkA.append({
        event: "input_validation_approved",
        traceId: "t",
        spanId: "s",
        tenantId: "x",
        payload: { a: 1, b: 2 },
        occurredAt: "2026-05-15T00:00:00.000Z",
      });
      const b = sinkB.append({
        event: "input_validation_approved",
        traceId: "t",
        spanId: "s",
        tenantId: "x",
        payload: { b: 2, a: 1 },
        occurredAt: "2026-05-15T00:00:00.000Z",
      });
      assert.equal(a.value.recordHash, b.value.recordHash);
    });
  });
});

// --- ADR-0008 §Decision.4: deterministic seal-from-events + anchor ---

const SEAL_EVENTS = [
  {
    recordId: "11111111-1111-1111-1111-111111111111",
    event: "policy_decision",
    traceId: "t1",
    spanId: "s1",
    tenantId: "system",
    occurredAt: "2026-06-01T00:00:00.000Z",
    payload: { action: "a1" },
  },
  {
    recordId: "22222222-2222-2222-2222-222222222222",
    event: "route_decision",
    traceId: "t2",
    spanId: "s2",
    tenantId: "system",
    occurredAt: "2026-06-01T00:00:01.000Z",
    payload: { action: "a2" },
  },
];

test("sealFromEvents is deterministic and byte-reproducible", () => {
  withTempSink((sinkA) => {
    withTempSink((sinkB) => {
      const headA = sinkA.sealFromEvents(SEAL_EVENTS);
      const headB = sinkB.sealFromEvents(SEAL_EVENTS);
      assert.equal(headA, headB);
      assert.equal(
        readFileSync(sinkA.sinkPath, "utf8"),
        readFileSync(sinkB.sinkPath, "utf8"),
      );
    });
  });
});

test("sealed chain verifies against its anchor", () => {
  withTempSink((sink) => {
    const head = sink.sealFromEvents(SEAL_EVENTS);
    const result = sink.verifyChain({
      expectedCount: SEAL_EVENTS.length,
      expectedHeadHash: head,
    });
    assert.equal(result.ok, true);
    assert.equal(result.recordsVerified, SEAL_EVENTS.length);
  });
});

test("sealFromEvents rejects an unknown event", () => {
  withTempSink((sink) => {
    assert.throws(() =>
      sink.sealFromEvents([{ ...SEAL_EVENTS[0], event: "garbage" }]),
    );
  });
});

test("tail truncation is detected by the anchor record count", () => {
  withTempSink((sink) => {
    const head = sink.sealFromEvents(SEAL_EVENTS);
    // Drop the last record — a valid prefix still link-verifies, so the
    // old forward-only walk passes. The anchor must catch it.
    const lines = readFileSync(sink.sinkPath, "utf8").trim().split("\n");
    writeFileSync(sink.sinkPath, lines.slice(0, -1).join("\n") + "\n");

    const unanchored = sink.verifyChain();
    assert.equal(unanchored.ok, true, "prefix still link-verifies (the gap)");

    const anchored = sink.verifyChain({
      expectedCount: SEAL_EVENTS.length,
      expectedHeadHash: head,
    });
    assert.equal(anchored.ok, false);
    assert.equal(anchored.error, "AUDIT_CHAIN_BROKEN");
  });
});

test("head hash mismatch is detected", () => {
  withTempSink((sink) => {
    sink.sealFromEvents(SEAL_EVENTS);
    const result = sink.verifyChain({
      expectedCount: SEAL_EVENTS.length,
      expectedHeadHash: "0".repeat(64),
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "AUDIT_CHAIN_BROKEN");
  });
});

test("absent ledger with a non-zero anchor fails", () => {
  withTempSink((sink) => {
    const result = sink.verifyChain({
      expectedCount: 3,
      expectedHeadHash: "0".repeat(64),
    });
    assert.equal(result.ok, false);
    assert.equal(result.error, "AUDIT_CHAIN_BROKEN");
  });
});

test("absent ledger with a zero anchor passes", () => {
  withTempSink((sink) => {
    const result = sink.verifyChain({
      expectedCount: 0,
      expectedHeadHash: QALA_GENESIS_HASH,
    });
    assert.equal(result.ok, true);
    assert.equal(result.recordsVerified, 0);
  });
});
