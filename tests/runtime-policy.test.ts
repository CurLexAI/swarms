import test from "node:test";
import assert from "node:assert/strict";
import { evaluateRuntimePolicy, RuntimePolicyError } from "../src/policy/runtime-policy.ts";
import { selectRuntimeProviders } from "../src/runtimePolicy.ts";

test("canonical policy rejects invalid legacy classification", () => {
  assert.throws(
    () => evaluateRuntimePolicy({ classification: "LEGACY_OPEN_CLOUD" as never }),
    (error: unknown) => error instanceof RuntimePolicyError && error.code === "INVALID_CLASSIFICATION",
  );
});

test("RESTRICTED data is local-control-plane only", () => {
  const decision = evaluateRuntimePolicy({
    classification: "RESTRICTED",
    requiresCodeGeneration: true,
    humanApprovedCloudEgress: true,
  });

  assert.equal(decision.allowed, true);
  assert.deepEqual(decision.providerOrder, ["ollama-qwen-local", "ollama-deepseek-local"]);
});

test("public burst can use approved/external providers only with human approval", () => {
  const unapproved = evaluateRuntimePolicy({
    classification: "PUBLIC",
    requiresLongContext: true,
  });
  assert.ok(!unapproved.providerOrder.includes("vertex-llama4"));
  assert.ok(!unapproved.providerOrder.includes("cursor-cloud"));

  const approved = evaluateRuntimePolicy({
    classification: "PUBLIC",
    requiresLongContext: true,
    humanApprovedCloudEgress: true,
  });
  assert.ok(approved.providerOrder.includes("vertex-llama4"));
  assert.ok(approved.providerOrder.includes("cursor-cloud"));
});

test("public code long-context can use Cursor only with human approval", () => {
  const unapproved = evaluateRuntimePolicy({
    classification: "PUBLIC",
    requiresCodeGeneration: true,
    requiresLongContext: true,
  });
  assert.ok(!unapproved.providerOrder.includes("cursor-cloud"));

  const approved = evaluateRuntimePolicy({
    classification: "PUBLIC",
    requiresCodeGeneration: true,
    requiresLongContext: true,
    humanApprovedCloudEgress: true,
  });
  assert.ok(approved.providerOrder.includes("cursor-cloud"));
});

test("public vision fails closed without human-approved cloud egress", () => {
  assert.throws(
    () => evaluateRuntimePolicy({ classification: "PUBLIC", requiresVision: true }),
    (error: unknown) => error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER",
  );
});

test("public vision uses approved Llama 4 cloud only after human approval", () => {
  const decision = evaluateRuntimePolicy({
    classification: "PUBLIC",
    requiresVision: true,
    humanApprovedCloudEgress: true,
  });

  assert.deepEqual(decision.providerOrder, ["vertex-llama4"]);
});

test("deprecated runtimePolicy adapter delegates to canonical provider ids", () => {
  const standard = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "STANDARD",
    allowModalProvider: true,
  });
  const burst = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "BURST",
    allowExternalProvider: true,
    allowModalProvider: true,
  });

  assert.equal(standard.allowed, true);
  assert.ok(standard.providers.includes("ollama-qwen-local"));
  assert.ok(standard.canonicalDecision);
  assert.equal(burst.allowed, true);
  assert.ok(burst.providers.includes("vertex-llama4"));
  assert.ok(burst.canonicalDecision);
});

test("deprecated runtimePolicy adapter blocks retired legacy cloud mode", () => {
  const decision = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "LEGACY_OPEN_CLOUD",
    allowExternalProvider: true,
  });

  assert.equal(decision.allowed, false);
  assert.deepEqual(decision.providers, []);
  assert.match(decision.reason, /LEGACY_OPEN_CLOUD/);
});
