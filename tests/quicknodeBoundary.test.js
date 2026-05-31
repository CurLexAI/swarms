import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join } from "node:path";
import {
  QuicknodeConfigurationError,
  QuicknodeIntegrationDisabledError,
  createQuicknodeRpcPort,
  sanitizeRpcUrl,
} from "../src/ports/quicknodeRpcPort.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const ENV_EXAMPLE = readFileSync(join(ROOT, ".env.example"), "utf8");
const PORT_SOURCE = readFileSync(join(ROOT, "src", "ports", "quicknodeRpcPort.ts"), "utf8");
const TRACKED_FILES = execFileSync("git", ["ls-files", "--cached", "--others", "--exclude-standard"], { cwd: ROOT, encoding: "utf8" })
  .split("\n")
  .filter(Boolean)
  .filter((file) => !file.startsWith("node_modules/"));

test("Quicknode is disabled unless explicitly configured", async () => {
  const port = createQuicknodeRpcPort({ enabled: false });

  assert.equal(port.provider, "quicknode");
  assert.equal(port.enabled, false);
  await assert.rejects(
    () => port.request({ method: "eth_blockNumber" }),
    QuicknodeIntegrationDisabledError,
  );
});

test("Quicknode enablement fails closed without secret-store RPC URL", () => {
  assert.throws(
    () => createQuicknodeRpcPort({ enabled: true }),
    QuicknodeConfigurationError,
  );
});

test("Quicknode RPC URL must use HTTPS and no userinfo credentials", () => {
  assert.throws(
    () => createQuicknodeRpcPort({ enabled: true, rpcUrl: "http://example.invalid/rpc" }),
    /HTTPS/,
  );
  assert.throws(
    () => createQuicknodeRpcPort({ enabled: true, rpcUrl: "https://user:pass@example.invalid/rpc" }),
    /username or password/,
  );
});

test("Quicknode factory never returns a live adapter before reviewed implementation exists", () => {
  const warnings = [];
  const port = createQuicknodeRpcPort(
    { enabled: true, rpcUrl: "https://public.example.invalid/rpc" },
    { warn: (_message, metadata) => warnings.push(metadata) },
  );

  assert.equal(port.enabled, false);
  assert.equal(warnings.length, 1);
  assert.equal(warnings[0].rpcUrl, "https://public.example.invalid/rpc");
});

test("Quicknode URL sanitizer redacts embedded token material", () => {
  const tokenizedUrl = [
    "https://",
    "abc123def456ghi789abc123",
    ".quiknode.pro/",
    "0123456789abcdef0123456789abcdef",
    "/?apikey=example-value",
  ].join("");
  const sanitized = sanitizeRpcUrl(tokenizedUrl);

  assert.equal(
    sanitized,
    "https://redacted.invalid/[REDACTED]/?apikey=%5BREDACTED%5D",
  );
  assert.doesNotMatch(sanitized, /abc123def456|0123456789abcdef|example-value/);
});

test("Quicknode environment example contains placeholders only", () => {
  assert.match(ENV_EXAMPLE, /QUICKNODE_ENABLED=false/);
  assert.match(ENV_EXAMPLE, /QUICKNODE_RPC_URL=__SET_IN_SECRET_STORE__/);
  assert.doesNotMatch(ENV_EXAMPLE, /QUICKNODE_RPC_URL=https?:\/\//);
});

test("Quicknode source boundary does not implement direct network RPC", () => {
  assert.doesNotMatch(PORT_SOURCE, /\bfetch\s*\(/);
  assert.doesNotMatch(PORT_SOURCE, /new\s+WebSocket\s*\(/);
  assert.match(PORT_SOURCE, /export interface Web3RpcPort/);
});



test("business logic does not access Quicknode configuration or RPC directly", () => {
  const offenders = [];
  for (const file of TRACKED_FILES.filter((name) => name.startsWith("src/") && !name.startsWith("src/ports/"))) {
    const text = readFileSync(join(ROOT, file), "utf8");
    if (/QUICKNODE_|quicknode|quiknode|eth_blockNumber|eth_call/i.test(text)) {
      offenders.push(file);
    }
  }

  assert.deepEqual(offenders, []);
});

test("tracked files do not commit tokenized Quicknode RPC URLs", () => {
  const offenders = [];
  for (const file of TRACKED_FILES) {
    const text = readFileSync(join(ROOT, file), "utf8");
    if (/https?:\/\/[^\s"'<>]*quicknode[^\s"'<>]*/i.test(text)) {
      offenders.push(file);
    }
    if (/https?:\/\/[^\s"'<>]*quiknode[^\s"'<>]*[A-Za-z0-9]{16,}/i.test(text)) {
      offenders.push(file);
    }
  }

  assert.deepEqual([...new Set(offenders)], []);
});
