import assert from "node:assert/strict";

import {
  EXTERNAL_PROVIDER_IDS,
  LOCAL_LLAMA_CPP_PROVIDER,
  isCopilotCiSetupOnly,
  isLegacyArchitectureBlocked,
  isRestrictedRouteLocalOnly,
  providerOrderForClassification,
  runtimePolicy,
} from "../src/policy/runtime-policy.js";

assert.equal(runtimePolicy.primaryArchitecture, "node_express_primary");
assert.equal(isLegacyArchitectureBlocked("fastapi_primary_gateway"), true);
assert.equal(isLegacyArchitectureBlocked("factory_driven_main_py"), true);
assert.equal(isLegacyArchitectureBlocked("public_llm_gateway"), true);

const restrictedProviderOrder = providerOrderForClassification("RESTRICTED");
assert.deepEqual(restrictedProviderOrder, [LOCAL_LLAMA_CPP_PROVIDER]);
assert.equal(isRestrictedRouteLocalOnly(), true);
assert.equal(
  restrictedProviderOrder.some((providerId) =>
    (EXTERNAL_PROVIDER_IDS as readonly string[]).includes(providerId),
  ),
  false,
);

assert.equal(isCopilotCiSetupOnly(), true);
assert.equal(runtimePolicy.copilotCi.mode, "setup_only");
assert.equal(runtimePolicy.copilotCi.noSecretsMode, true);
assert.equal(runtimePolicy.copilotCi.liveProviderCallsAllowed, false);

assert.deepEqual(providerOrderForClassification("CONFIDENTIAL"), [
  LOCAL_LLAMA_CPP_PROVIDER,
]);
assert.deepEqual(providerOrderForClassification("PUBLIC"), [
  "local_ollama",
  LOCAL_LLAMA_CPP_PROVIDER,
]);
assert.deepEqual(providerOrderForClassification("INTERNAL"), [
  "local_ollama",
  LOCAL_LLAMA_CPP_PROVIDER,
]);

console.log("runtime-policy: current sovereign guard passed");
#!/usr/bin/env tsx
import { selectRuntimeProviders } from "../src/runtimePolicy.ts";

interface CheckResult {
  readonly name: string;
  readonly ok: boolean;
  readonly detail: string;
}

function runChecks(): readonly CheckResult[] {
  const restricted = selectRuntimeProviders({
    dataClassification: "RESTRICTED",
    mode: "BURST",
    allowExternalProvider: true,
    allowModalProvider: true,
    allowNotebookRuntime: true,
  });
  const copilotGeneral = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "COPILOT_CLOUD_AGENT",
    purpose: "GENERAL",
  });
  const copilotSetup = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "COPILOT_CLOUD_AGENT",
    purpose: "CI_SETUP",
  });
  const legacy = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "LEGACY_OPEN_CLOUD",
    allowExternalProvider: true,
  });

  return [
    {
      name: "restricted-data-local-only",
      ok: restricted.allowed && restricted.providers.length === 1 && restricted.providers[0] === "local_llama_cpp",
      detail: `providers=${restricted.providers.join(",")}`,
    },
    {
      name: "copilot-cloud-agent-general-blocked",
      ok: !copilotGeneral.allowed && copilotGeneral.providers.length === 0,
      detail: copilotGeneral.reason,
    },
    {
      name: "copilot-cloud-agent-ci-setup-only",
      ok: copilotSetup.allowed && copilotSetup.providers.length === 1 && copilotSetup.providers[0] === "copilot_ci_setup",
      detail: copilotSetup.reason,
    },
    {
      name: "legacy-open-cloud-blocked",
      ok: !legacy.allowed && legacy.providers.length === 0,
      detail: legacy.reason,
    },
  ];
}

const results = runChecks();
for (const result of results) {
  const label = result.ok ? "VERIFIED" : "FAILED";
  console.log(`${label}: ${result.name} — ${result.detail}`);
}

if (results.some((result) => !result.ok)) {
  process.exit(1);
}
