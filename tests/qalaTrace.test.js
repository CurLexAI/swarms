import test from "node:test";
import assert from "node:assert/strict";

import {
  QALA_HEADER,
  QalaTraceError,
  childSpan,
  fromHeaders,
  newTrace,
  toHeaders,
} from "../src/security/qalaTrace.js";

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

test("newTrace generates v4 uuids and zero parent", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  assert.match(ctx.traceId, UUID_V4);
  assert.match(ctx.spanId, UUID_V4);
  assert.notEqual(ctx.traceId, ctx.spanId);
  assert.equal(ctx.parentSpanId, null);
  assert.equal(ctx.tenantId, "tenant-A");
  assert.equal(ctx.phase, "input_validation");
});

test("newTrace rejects unknown phase", () => {
  assert.throws(() => newTrace("tenant-A", "garbage"), QalaTraceError);
});

test("newTrace rejects empty tenant", () => {
  assert.throws(() => newTrace("", "input_validation"), QalaTraceError);
});

test("newTrace rejects tenant with whitespace", () => {
  assert.throws(() => newTrace("tenant A", "input_validation"), QalaTraceError);
});

test("newTrace rejects oversize tenant", () => {
  assert.throws(() => newTrace("t".repeat(200), "input_validation"), QalaTraceError);
});

test("childSpan inherits trace and tenant", () => {
  const parent = newTrace("tenant-A", "input_validation");
  const child = childSpan(parent, "model_call");
  assert.equal(child.traceId, parent.traceId);
  assert.equal(child.tenantId, parent.tenantId);
  assert.equal(child.parentSpanId, parent.spanId);
  assert.notEqual(child.spanId, parent.spanId);
  assert.equal(child.phase, "model_call");
});

test("childSpan rejects unknown phase", () => {
  const parent = newTrace("tenant-A", "input_validation");
  assert.throws(() => childSpan(parent, "garbage"), QalaTraceError);
});

test("toHeaders / fromHeaders round-trip", () => {
  const ctx = newTrace("tenant-A", "policy_check");
  const restored = fromHeaders(toHeaders(ctx));
  assert.deepEqual(restored, ctx);
});

test("toHeaders / fromHeaders round-trip with parent", () => {
  const parent = newTrace("tenant-A", "input_validation");
  const child = childSpan(parent, "audit_emit");
  const restored = fromHeaders(toHeaders(child));
  assert.deepEqual(restored, child);
});

test("fromHeaders is case-insensitive", () => {
  const ctx = newTrace("tenant-A", "audit_emit");
  const headers = toHeaders(ctx);
  const upper = {};
  for (const [k, v] of Object.entries(headers)) upper[k.toUpperCase()] = v;
  const restored = fromHeaders(upper);
  assert.deepEqual(restored, ctx);
});

test("fromHeaders fails closed on missing trace id", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  delete headers[QALA_HEADER.TRACE_ID];
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders fails closed on missing span id", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  delete headers[QALA_HEADER.SPAN_ID];
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders fails closed on missing tenant", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  delete headers[QALA_HEADER.TENANT_ID];
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders fails closed on missing phase", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  delete headers[QALA_HEADER.PHASE];
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders rejects malformed uuid", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  headers[QALA_HEADER.TRACE_ID] = "not-a-uuid";
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders rejects malformed parent span id", () => {
  const parent = newTrace("tenant-A", "input_validation");
  const child = childSpan(parent, "model_call");
  const headers = toHeaders(child);
  headers[QALA_HEADER.PARENT_SPAN_ID] = "not-a-uuid";
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders rejects unknown phase", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  headers[QALA_HEADER.PHASE] = "garbage";
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders rejects malformed tenant", () => {
  const ctx = newTrace("tenant-A", "input_validation");
  const headers = toHeaders(ctx);
  headers[QALA_HEADER.TENANT_ID] = "bad tenant id";
  assert.equal(fromHeaders(headers), null);
});

test("fromHeaders rejects empty header map", () => {
  assert.equal(fromHeaders({}), null);
});

test("toHeaders does NOT emit Authorization / Cookie / secret-shapes", () => {
  const ctx = newTrace("tenant-A", "model_call");
  const headers = toHeaders(ctx);
  const lowerKeys = Object.keys(headers).map((k) => k.toLowerCase());
  assert.ok(!lowerKeys.includes("authorization"));
  assert.ok(!lowerKeys.includes("cookie"));
  assert.ok(!lowerKeys.includes("x-api-key"));
  const SECRET_SHAPES = [
    /Bearer\s+/i,
    /\bsk-[A-Za-z0-9_-]{8,}/i,
    /\bghp_[A-Za-z0-9_]{8,}/,
    /\bAKIA[0-9A-Z]{8,}/,
    /\.modal\.run/i,
  ];
  for (const value of Object.values(headers)) {
    for (const pattern of SECRET_SHAPES) {
      assert.equal(pattern.test(value), false, `header leaked: ${value}`);
    }
  }
});

test("phase enum is closed (sanity)", () => {
  const valid = [
    "auth_check",
    "input_validation",
    "policy_check",
    "egress_check",
    "model_call",
    "output_validation",
    "audit_emit",
  ];
  for (const p of valid) {
    const ctx = newTrace("tenant-A", p);
    assert.equal(ctx.phase, p);
  }
});
