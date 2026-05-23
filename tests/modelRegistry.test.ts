import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { loadModelRegistry } from "../src/models/modelRegistry.ts";

test("loadModelRegistry loads canonical registry", () => {
  const registry = loadModelRegistry();
  assert.ok(registry.models.length >= 3);
  assert.equal(registry.models[0].id, "qwen-coder-local");
});

test("loadModelRegistry rejects duplicate model ids", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "model-registry-"));
  const file = path.join(dir, "models.registry.json");
  fs.writeFileSync(file, JSON.stringify({
    models: [
      { id: "dup", provider: "ollama", model: "m1", profile: "local_only", use: ["x"], endpoint: "http://127.0.0.1:11434" },
      { id: "dup", provider: "modal", model: "m2", profile: "sanitized_cloud", use: ["x"], app: "curlexai-agents" }
    ]
  }));

  assert.throws(() => loadModelRegistry(file), /duplicate model id/);
  fs.rmSync(dir, { recursive: true, force: true });
});
