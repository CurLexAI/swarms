import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";


const SOURCE_PATH = path.resolve("src/services/unifiedAgentAdapter.ts");

async function loadAuditServiceOrSkip(t) {
  try {
    const mod = await import("../src/services/AuditService.ts");
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
  const patchedSource = source
    .replace('import yaml from "js-yaml";', 'const yaml = { load: () => ({ agents: [] }) };')
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
    `unifiedAgentAdapter.node-dispatch.${process.pid}.${Date.now()}.${Math.random().toString(16).slice(2)}.mjs`
  );

  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, transpiled.outputText, "utf8");

  const mod = await import(pathToFileURL(outFile).href);

  fs.unlinkSync(outFile);
  return mod;
}

test("UnifiedAgentAdapter dispatches node runtime to canonical runAgent with validated payload", async (t) => {
  const runAgentCalls = [];
  const runAgentStub = async (payload) => {
    runAgentCalls.push(payload);
    return { output: "node-result", provider: "stub" };
  };

  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter } = loaded;

  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const taskUpdates = [];

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => {
    taskUpdates.push(args);
  };

  t.after(() => {
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.getNodeDispatcher = async () => runAgentStub;
  adapter.agents = new Map([
    [
      "node-agent",
      {
        id: "node-agent",
        name: "Node Agent",
        role: "test",
        runtime: "node",
        allowedScopes: ["scope:execute"],
        capabilities: ["node_execution"]
      }
    ]
  ]);

  const result = await adapter.executeAgent(
    "node-agent",
    "user-1",
    {
      tenant_id: "tenant-1",
      input: "run test",
      metadata: { trace_id: "trace-123" }
    },
    ["scope:execute"],
    "tenant-1"  // P0: serverPrincipalTenantId from auth context
  );

  assert.equal(runAgentCalls.length, 1);
  assert.deepEqual(runAgentCalls[0], {
    agentId: "node-agent",
    input: "run test",
    payload: {
      tenant_id: "tenant-1",
      input: "run test",
      metadata: { trace_id: "trace-123" }
    },
    context: "api",
    isAdmin: true
  });

  assert.equal(result.status, "success");
  assert.deepEqual(result.data, { output: "node-result", provider: "stub" });
  assert.equal(taskUpdates.length, 1);
  assert.equal(taskUpdates[0][1], "COMPLETED");
});

test("UnifiedAgentAdapter returns real node execution output for hybrid agents (intentional split)", async (t) => {
  const runAgentStub = async () => ({ output: "hybrid-node-output", details: { routedTo: "node" } });
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter } = loaded;

  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async () => {};

  t.after(() => {
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.getNodeDispatcher = async () => runAgentStub;
  adapter.agents = new Map([
    [
      "hybrid-agent",
      {
        id: "hybrid-agent",
        name: "Hybrid Agent",
        role: "test",
        runtime: "hybrid",
        allowedScopes: ["scope:execute"],
        capabilities: ["node_execution"]
      }
    ]
  ]);

  const result = await adapter.executeAgent(
    "hybrid-agent",
    "user-1",
    {
      tenant_id: "tenant-1",
      input: "route check",
      metadata: { mode: "hybrid" }
    },
    ["scope:execute"],
    "tenant-1"  // P0: serverPrincipalTenantId from auth context
  );

  assert.equal(result.status, "success");
  assert.deepEqual(result.data, { output: "hybrid-node-output", details: { routedTo: "node" } });
});

test("UnifiedAgentAdapter marks task FAILED when node dispatch throws runtime failure", async (t) => {
  const runAgentStub = async () => {
    const error = new Error("provider crashed");
    error.code = "AGENT_EXECUTION_FAILED";
    throw error;
  };

  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter } = loaded;

  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const taskUpdates = [];

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => {
    taskUpdates.push(args);
  };

  t.after(() => {
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.getNodeDispatcher = async () => runAgentStub;
  adapter.agents = new Map([
    [
      "node-agent",
      {
        id: "node-agent",
        name: "Node Agent",
        role: "test",
        runtime: "node",
        allowedScopes: ["scope:execute"],
        capabilities: ["node_execution"]
      }
    ]
  ]);

  await assert.rejects(
    () =>
      adapter.executeAgent(
        "node-agent",
        "user-1",
        {
          tenant_id: "tenant-1",
          input: "run test",
          metadata: { trace_id: "trace-err" }
        },
        ["scope:execute"],
        "tenant-1"  // P0: serverPrincipalTenantId from auth context
      ),
    (error) => {
      assert.match(error.message, /^RUNTIME_FAILURE: Node runtime execution failed for agent node-agent:/);
      return true;
    }
  );

  assert.equal(taskUpdates.length, 1);
  assert.equal(taskUpdates[0][1], "FAILED");
  assert.match(taskUpdates[0][2].error, /^RUNTIME_FAILURE: Node runtime execution failed for agent node-agent:/);
});
