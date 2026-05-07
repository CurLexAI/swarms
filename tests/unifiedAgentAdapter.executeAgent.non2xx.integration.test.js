import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";


const SOURCE_PATH = path.resolve("src/services/unifiedAgentAdapter.ts");

async function loadAuditServiceOrSkip(t) {
  try {
    const mod = await import("../src/services/AuditService.js");
    return mod.AuditService;
  } catch {
    t.skip("AuditService module is not available for direct ESM import in this runtime");
    return null;
  }
}

async function loadTypeScriptOrSkip(t) {
  try {
    const tsModule = await import("typescript");
    return tsModule.default ?? tsModule;
  } catch {
    t.skip("typescript dependency is not installed in this runtime");
    return null;
  }
}


async function loadUnifiedAgentAdapterFromTs(t) {
  const ts = await loadTypeScriptOrSkip(t);
  if (!ts) return null;
  const source = fs.readFileSync(SOURCE_PATH, "utf8");
  const patchedSource = source.replace(
    'import yaml from "js-yaml";',
    'const yaml = { load: () => ({ agents: [] }) };'
  )
    .replace('import { v4 as uuidv4 } from "uuid";\n', "")
    .replaceAll("uuidv4()", "randomUUID()");
  const transpiled = ts.transpileModule(patchedSource, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022
    },
    fileName: SOURCE_PATH
  });

  const outFile = path.join(
    process.cwd(),
    "src/services",
    `unifiedAgentAdapter.test.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.mjs`
  );
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, transpiled.outputText, "utf8");

  const mod = await import(pathToFileURL(outFile).href);
  fs.unlinkSync(outFile);
  return mod;
}

test("UnifiedAgentAdapter.executeAgent marks task FAILED and throws sanitized client-safe error on non-2xx python response", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalFetch = global.fetch;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;

  let jsonCalled = false;
  const updateTaskStatusCalls = [];

  const dangerousBody = `Traceback (most recent call last): ValueError
db_password=hunter2 token=abc123 INTERNAL ERROR: stack frame exploded`;

  global.fetch = async () => ({
    ok: false,
    status: 500,
    text: async () => dangerousBody,
    json: async () => {
      jsonCalled = true;
      return { ok: true, hidden: "must-not-be-used" };
    }
  });

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => {
    updateTaskStatusCalls.push(args);
  };

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([
    [
      "py-agent",
      {
        id: "py-agent",
        name: "Python Agent",
        role: "test",
        runtime: "python",
        allowedScopes: ["scope:execute"]
      }
    ]
  ]);

  process.env.PYTHON_BACKEND_URL = "http://python-backend.invalid";

  await assert.rejects(
    async () =>
      adapter.executeAgent(
        "py-agent",
        "user-1",
        {
          tenant_id: "tenant-1",
          input: "run",
          metadata: { source: "integration-test" }
        },
        ["scope:execute"],
        "tenant-1"  // P0: serverPrincipalTenantId from auth context
      ),
    (error) => {
      assert.match(error.message, /Python engine request failed with status 500/);
      assert.match(error.message, /\(ref: [0-9a-f]{8}\)/i);
      assert.doesNotMatch(error.message, /Traceback/i);
      assert.doesNotMatch(error.message, /db_password/i);
      assert.doesNotMatch(error.message, /password/i);
      assert.doesNotMatch(error.message, /token/i);
      assert.doesNotMatch(error.message, /INTERNAL ERROR: stack frame exploded/i);
      return true;
    }
  );

  assert.equal(jsonCalled, false, "response.json() must not be called when response.ok=false");
  assert.equal(updateTaskStatusCalls.length, 1);
  assert.equal(updateTaskStatusCalls[0][1], "FAILED");
  assert.match(updateTaskStatusCalls[0][2].error, /Python engine request failed with status 500/);
  assert.match(updateTaskStatusCalls[0][2].error, /\(ref: [0-9a-f]{8}\)/i);
  assert.doesNotMatch(updateTaskStatusCalls[0][2].error, /Traceback|db_password|token/i);
});

test("UnifiedAgentAdapter.executeAgent maps network errors to sanitized 502 contract", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalFetch = global.fetch;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;

  const updateTaskStatusCalls = [];

  global.fetch = async () => {
    throw new Error("connect ECONNREFUSED python-backend.internal");
  };

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => {
    updateTaskStatusCalls.push(args);
  };

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([
    [
      "py-agent",
      {
        id: "py-agent",
        name: "Python Agent",
        role: "test",
        runtime: "python",
        allowedScopes: ["scope:execute"]
      }
    ]
  ]);

  process.env.PYTHON_BACKEND_URL = "http://python-backend.invalid";

  await assert.rejects(
    async () =>
      adapter.executeAgent(
        "py-agent",
        "user-1",
        {
          tenant_id: "tenant-1",
          input: "run",
          metadata: { source: "integration-test" }
        },
        ["scope:execute"],
        "tenant-1"  // P0: serverPrincipalTenantId from auth context
      ),
    (error) => {
      assert.match(error.message, /Python engine request failed with status 502/);
      assert.match(error.message, /\(ref: [0-9a-f]{8}\)/i);
      assert.doesNotMatch(error.message, /ECONNREFUSED/i);
      assert.doesNotMatch(error.message, /python-backend\.internal/i);
      return true;
    }
  );

  assert.equal(updateTaskStatusCalls.length, 1);
  assert.equal(updateTaskStatusCalls[0][1], "FAILED");
  assert.match(updateTaskStatusCalls[0][2].error, /Python engine request failed with status 502/);
  assert.match(updateTaskStatusCalls[0][2].error, /\(ref: [0-9a-f]{8}\)/i);
  assert.doesNotMatch(updateTaskStatusCalls[0][2].error, /ECONNREFUSED|python-backend\.internal/i);
});
