#!/usr/bin/env tsx
// SPDX-License-Identifier: MIT
// Licensed under MIT

import assert from "node:assert/strict";
import {
  evaluateRuntimePolicy,
  isCopilotCiSetupOnly,
  isLegacyArchitectureBlocked,
  RuntimePolicyError,
  runtimePolicy,
} from "../src/policy/runtime-policy.ts";

function assertThrowsPolicyCode(code: RuntimePolicyError["code"], fn: () => unknown): void {
  assert.throws(
    fn,
    (error: unknown) => error instanceof RuntimePolicyError && error.code === code,
    `runtime policy must fail closed with ${code}`,
  );
}

assert.equal(runtimePolicy.primaryArchitecture, "node_express_primary");
assert.equal(isLegacyArchitectureBlocked("fastapi_primary_gateway"), true);
assert.equal(isLegacyArchitectureBlocked("factory_driven_main_py"), true);
assert.equal(isLegacyArchitectureBlocked("public_llm_gateway"), true);
assert.equal(isCopilotCiSetupOnly(), true);

const restricted = evaluateRuntimePolicy({
  classification: "RESTRICTED",
  requiresCodeGeneration: true,
  humanApprovedCloudEgress: true,
});
assert.deepEqual(restricted.providerOrder, ["ollama-qwen-local", "ollama-deepseek-local"]);

const confidential = evaluateRuntimePolicy({
  classification: "CONFIDENTIAL",
  requiresLongContext: true,
  humanApprovedCloudEgress: true,
});
assert.equal(confidential.providerOrder.includes("vertex-llama4"), false);
assert.equal(confidential.providerOrder.includes("cursor-cloud"), false);

assertThrowsPolicyCode("NO_ALLOWED_PROVIDER", () =>
  evaluateRuntimePolicy({ classification: "PUBLIC", requiresVision: true }),
);

const approvedVision = evaluateRuntimePolicy({
  classification: "PUBLIC",
  requiresVision: true,
  humanApprovedCloudEgress: true,
});
assert.deepEqual(approvedVision.providerOrder, ["vertex-llama4"]);

assertThrowsPolicyCode("INVALID_CLASSIFICATION", () =>
  evaluateRuntimePolicy({ classification: "LEGACY_OPEN_CLOUD" as never }),
);

console.log("Runtime policy check passed.");
import { evaluateRuntimePolicy, RuntimePolicyError, type ProviderId } from "../src/policy/runtime-policy.ts";
import { selectRuntimeProviders } from "../src/runtimePolicy.ts";

interface CheckResult {
  readonly name: string;
  readonly passed: boolean;
  readonly detail: string;
}

function check(name: string, assertion: () => void): CheckResult {
  try {
    assertion();
    return { name, passed: true, detail: "VERIFIED" };
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    return { name, passed: false, detail };
  }
}

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message);
  }
}

function assertNoExternalProviders(providers: readonly ProviderId[]): void {
  assert(
    providers.every((provider) => provider !== "vertex-llama4" && provider !== "cursor-cloud"),
    `external providers escaped sovereign boundary: ${providers.join(",")}`,
  );
}

const results: CheckResult[] = [
  check("restricted runtime remains local-control-plane only", () => {
    const decision = evaluateRuntimePolicy({
      classification: "RESTRICTED",
      requiresCodeGeneration: true,
      humanApprovedCloudEgress: true,
    });
    assert(decision.allowed, "restricted decision should be allowed through local runtime");
    assert(
      decision.providerOrder.every(
        (provider) => provider === "ollama-qwen-local" || provider === "ollama-deepseek-local",
      ),
      `restricted providers escaped local boundary: ${decision.providerOrder.join(",")}`,
    );
  }),
  check("confidential policy excludes external cloud", () => {
    const decision = evaluateRuntimePolicy({
      classification: "CONFIDENTIAL",
      requiresLongContext: true,
      humanApprovedCloudEgress: true,
    });
    assertNoExternalProviders(decision.providerOrder);
  }),
  check("public vision requires human-approved cloud egress", () => {
    let blocked = false;
    try {
      evaluateRuntimePolicy({ classification: "PUBLIC", requiresVision: true });
    } catch (error) {
      blocked = error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER";
    }
    assert(blocked, "public vision without human approval must fail closed");

    const approved = evaluateRuntimePolicy({
      classification: "PUBLIC",
      requiresVision: true,
      humanApprovedCloudEgress: true,
    });
    assert(
      approved.providerOrder.length === 1 && approved.providerOrder[0] === "vertex-llama4",
      `unexpected approved vision providers: ${approved.providerOrder.join(",")}`,
    );
  }),
  check("invalid classification fails closed", () => {
    let blocked = false;
    try {
      evaluateRuntimePolicy({ classification: "LEGACY_OPEN_CLOUD" as never });
    } catch (error) {
      blocked = error instanceof RuntimePolicyError && error.code === "INVALID_CLASSIFICATION";
    }
    assert(blocked, "invalid legacy classification must fail closed");
  }),
  check("legacy runtime adapter blocks retired open cloud mode", () => {
    const decision = selectRuntimeProviders({
      dataClassification: "PUBLIC",
      mode: "LEGACY_OPEN_CLOUD",
      allowExternalProvider: true,
    });
    assert(!decision.allowed, "legacy open cloud mode must remain blocked");
    assert(decision.providers.length === 0, "blocked legacy mode must not return providers");
  }),
];

for (const result of results) {
  const prefix = result.passed ? "✅" : "❌";
  console.log(`${prefix} ${result.name}: ${result.detail}`);
}

if (results.some((result) => !result.passed)) {
  process.exit(1);
}
