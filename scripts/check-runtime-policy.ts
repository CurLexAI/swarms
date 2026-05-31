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
