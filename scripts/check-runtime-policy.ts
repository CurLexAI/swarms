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
