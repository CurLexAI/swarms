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
