import test from "node:test";
import assert from "node:assert/strict";
import { selectRuntimeProviders } from "../src/runtimePolicy.ts";

test("LEGACY_OPEN_CLOUD is blocked", () => {
  const decision = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "LEGACY_OPEN_CLOUD",
    allowExternalProvider: true,
  });

  assert.equal(decision.allowed, false);
  assert.deepEqual(decision.providers, []);
  assert.match(decision.reason, /LEGACY_OPEN_CLOUD/);
});

test("RESTRICTED data is local-only", () => {
  const decision = selectRuntimeProviders({
    dataClassification: "RESTRICTED",
    mode: "STANDARD",
  });

  assert.equal(decision.allowed, true);
  assert.deepEqual(decision.providers, ["local_llama_cpp"]);
});

test("public burst can use an external provider", () => {
  const decision = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "BURST",
    allowExternalProvider: true,
  });

  assert.equal(decision.allowed, true);
  assert.ok(decision.providers.includes("external_provider"));
});

test("notebooks are public experiment only", () => {
  const publicExperiment = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "NOTEBOOK",
    allowNotebookRuntime: true,
  });
  const restrictedNotebook = selectRuntimeProviders({
    dataClassification: "RESTRICTED",
    mode: "NOTEBOOK",
    allowNotebookRuntime: true,
  });

  assert.equal(publicExperiment.allowed, true);
  assert.deepEqual(publicExperiment.providers, ["notebook_public_experiment"]);
  assert.equal(restrictedNotebook.allowed, true);
  assert.deepEqual(restrictedNotebook.providers, ["local_llama_cpp"]);
});

test("Copilot cloud agent is CI setup only", () => {
  const ciSetup = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "COPILOT_CLOUD_AGENT",
    purpose: "CI_SETUP",
  });
  const generalUse = selectRuntimeProviders({
    dataClassification: "PUBLIC",
    mode: "COPILOT_CLOUD_AGENT",
    purpose: "GENERAL",
  });

  assert.equal(ciSetup.allowed, true);
  assert.deepEqual(ciSetup.providers, ["copilot_ci_setup"]);
  assert.equal(generalUse.allowed, false);
  assert.deepEqual(generalUse.providers, []);
});

test("restricted provider order ignores external/notebook/modal flags", () => {
  const decision = selectRuntimeProviders({
    dataClassification: "RESTRICTED",
    mode: "NOTEBOOK",
    allowExternalProvider: true,
    allowModalProvider: true,
    allowNotebookRuntime: true,
  });

  assert.equal(decision.allowed, true);
  assert.deepEqual(decision.providers, ["local_llama_cpp"]);
});
