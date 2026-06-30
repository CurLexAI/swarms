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

test("public burst remains local-only and fails closed without local long-context support", () => {
  assert.throws(
    () => evaluateRuntimePolicy({
      classification: "PUBLIC",
      requiresLongContext: true,
      humanApprovedCloudEgress: true,
    }),
    (error: unknown) => error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER",
  );
});

test("public code long-context fails closed in local sovereign only mode", () => {
  assert.throws(
    () => evaluateRuntimePolicy({
      classification: "PUBLIC",
      requiresCodeGeneration: true,
      requiresLongContext: true,
      humanApprovedCloudEgress: true,
    }),
    (error: unknown) => error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER",
  );
});

test("public vision fails closed without local vision provider", () => {
  assert.throws(
    () => evaluateRuntimePolicy({ classification: "PUBLIC", requiresVision: true }),
    (error: unknown) => error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER",
  );
});

test("public vision remains blocked even after cloud egress approval", () => {
  assert.throws(
    () => evaluateRuntimePolicy({
      classification: "PUBLIC",
      requiresVision: true,
      humanApprovedCloudEgress: true,
    }),
    (error: unknown) => error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER",
  );
});

test("deprecated runtimePolicy adapter delegates to canonical local provider ids", () => {
  const standard = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "STANDARD",
  });
  const burst = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "BURST",
    allowExternalProvider: true,
  });

  assert.equal(standard.allowed, true);
  assert.ok(standard.providers.includes("ollama-qwen-local"));
  assert.ok(standard.canonicalDecision);
  assert.equal(burst.allowed, false);
  assert.deepEqual(burst.providers, []);
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
