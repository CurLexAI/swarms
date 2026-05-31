import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const TSX_BIN = join(ROOT, "node_modules", ".bin", "tsx");
const SOURCE = join(ROOT, "src", "services", "huggingface.ts");

function evaluate(script) {
  const result = spawnSync(TSX_BIN, ["--eval", script], {
    cwd: ROOT,
    encoding: "utf8",
    env: {
      ...process.env,
      HF_TOKEN: "__SET_IN_SECRET_STORE__",
      HF_MODEL_REPO: "approved-owner/approved-model",
      HF_INTEGRATION_MODE: "disabled"
    },
    timeout: 20_000
  });

  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}

test("Hugging Face boundary is disabled by default even with env names present", () => {
  const decision = evaluate(`
    import { createHuggingFaceArtifactPort, readHuggingFaceArtifactRequest } from ${JSON.stringify(SOURCE)};
    (async () => {
      const port = createHuggingFaceArtifactPort();
      const decision = await port.evaluate(readHuggingFaceArtifactRequest());
      process.stdout.write(JSON.stringify(decision));
    })();
  `);

  assert.equal(decision.enabled, false);
  assert.equal(decision.mode, "disabled");
  assert.match(decision.reason, /disabled by default/i);
});

test("Hugging Face service boundary contains no live network callsite or endpoint literal", () => {
  const source = readFileSync(SOURCE, "utf8");

  assert.doesNotMatch(source, /\bfetch\s*\(/);
  assert.doesNotMatch(source, /https?:\/\//i);
  assert.doesNotMatch(source, /huggingface\.co/i);
});

test("Hugging Face boundary rejects missing model repository without network I/O", () => {
  const decision = evaluate(`
    import { OfflineHuggingFaceArtifactAdapter } from ${JSON.stringify(SOURCE)};
    (async () => {
      const port = new OfflineHuggingFaceArtifactAdapter();
      const decision = await port.evaluate({ modelRepo: "   " });
      process.stdout.write(JSON.stringify(decision));
    })();
  `);

  assert.equal(decision.enabled, false);
  assert.equal(decision.mode, "disabled");
  assert.match(decision.reason, /HF_MODEL_REPO/);
});


test("Hugging Face mock adapter supports dependency injection without network I/O", () => {
  const decision = evaluate(`
    import { MockHuggingFaceArtifactAdapter } from ${JSON.stringify(SOURCE)};
    (async () => {
      const port = new MockHuggingFaceArtifactAdapter({
        enabled: false,
        mode: "disabled",
        reason: "MOCK_ONLY: dependency injection boundary"
      });
      const decision = await port.evaluate({ modelRepo: "approved-owner/approved-model" });
      process.stdout.write(JSON.stringify(decision));
    })();
  `);

  assert.equal(decision.enabled, false);
  assert.equal(decision.reason, "MOCK_ONLY: dependency injection boundary");
});
