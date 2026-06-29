#!/usr/bin/env tsx
// SPDX-License-Identifier: MIT
// Licensed under MIT

import {
  evaluateRuntimePolicy,
  isCopilotCiSetupOnly,
  isLegacyArchitectureBlocked,
  RuntimePolicyError,
  runtimePolicy,
  type ProviderId,
} from "../src/policy/runtime-policy.ts";

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
  check("runtime architecture blocks retired primary modes", () => {
    assert(runtimePolicy.primaryArchitecture === "node_express_primary", "unexpected primary architecture");
    assert(isLegacyArchitectureBlocked("fastapi_primary_gateway"), "FastAPI gateway must remain blocked");
    assert(isLegacyArchitectureBlocked("factory_driven_main_py"), "main.py factory mode must remain blocked");
    assert(isLegacyArchitectureBlocked("public_llm_gateway"), "public LLM gateway must remain blocked");
    assert(isCopilotCiSetupOnly(), "Copilot CI must remain setup-only/no-secrets");
  }),
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
  check("confidential long-context fails closed without local capability", () => {
    let blocked = false;
    try {
      evaluateRuntimePolicy({
        classification: "CONFIDENTIAL",
        requiresLongContext: true,
        humanApprovedCloudEgress: true,
      });
    } catch (error) {
      blocked = error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER";
    }
    assert(blocked, "confidential long-context must fail closed in local sovereign only mode");
  }),
  check("public vision fails closed without local vision provider", () => {
    let blocked = false;
    try {
      evaluateRuntimePolicy({ classification: "PUBLIC", requiresVision: true });
    } catch (error) {
      blocked = error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER";
    }
    assert(blocked, "public vision without human approval must fail closed");

    let approvedBlocked = false;
    try {
      evaluateRuntimePolicy({
        classification: "PUBLIC",
        requiresVision: true,
        humanApprovedCloudEgress: true,
      });
    } catch (error) {
      approvedBlocked = error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER";
    }
    assert(approvedBlocked, "public vision with cloud approval must still fail closed without local vision");
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
];

for (const result of results) {
  const prefix = result.passed ? "✅" : "❌";
  console.log(`${prefix} ${result.name}: ${result.detail}`);
}

if (results.some((result) => !result.passed)) {
  process.exit(1);
}

console.log("Runtime policy check passed.");
