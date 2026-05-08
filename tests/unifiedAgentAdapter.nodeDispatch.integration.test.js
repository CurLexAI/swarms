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
  );


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

test("UnifiedAgentAdapter rejects malformed downstream object that passes JSON parsing but fails quality verification", async (t) => {
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
  adapter.getNodeDispatcher = async () => async () => ({ traceId: "x-123" });
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
        { tenant_id: "tenant-1", input: "run test" },
        ["scope:execute"],
        "tenant-1"
      ),
    (error) => {
      assert.match(error.message, /UNVERIFIED_RUNTIME: downstream payload failed verification/i);
      return true;
    }
  );

  assert.equal(taskUpdates.length, 1);
  assert.equal(taskUpdates[0][1], "FAILED");
  assert.match(taskUpdates[0][2].blocker, /UNVERIFIED_RUNTIME/);
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

test("UnifiedAgentAdapter accepts valid downstream payload when quality verification requirements are met", async (t) => {
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
  adapter.getNodeDispatcher = async () => async () => ({ message: "ok", details: { source: "test" } });
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

  const response = await adapter.executeAgent(
    "node-agent",
    "user-1",
    { tenant_id: "tenant-1", input: "run test" },
    ["scope:execute"],
    "tenant-1"
  );

  assert.equal(response.status, "success");
  assert.deepEqual(response.data, { message: "ok", details: { source: "test" } });
  assert.equal(taskUpdates.length, 1);
  assert.equal(taskUpdates[0][1], "COMPLETED");
});

test("UnifiedAgentAdapter logs EXECUTE_<TYPE>_WITHOUT_REASONING action when reasoning is disabled", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter } = loaded;

  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const logActions = [];

  AuditService.logAction = async (entry) => {
    logActions.push(entry);
  };
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async () => {};

  t.after(() => {
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.getNodeDispatcher = async () => async () => ({ output: "ok" });
  adapter.agents = new Map([
    [
      "node-agent",
      {
        id: "node-agent",
        name: "Node Agent",
        role: "test",
        runtime: "node",
        allowedScopes: ["scope:execute"],
        capabilities: ["node_execution"],
        enable_reasoning: false
      }
    ]
  ]);

  await adapter.executeAgent("node-agent", "user-1", { tenant_id: "tenant-1", input: "x" }, ["scope:execute"], "tenant-1");

  assert.equal(logActions.length, 1);
  assert.equal(logActions[0].action, "EXECUTE_NODE_WITHOUT_REASONING");
  assert.equal(logActions[0].payload.reasoning_enabled, false);
});

test("UnifiedAgentAdapter logs EXECUTE_<TYPE>_WITH_REASONING action when reasoning is enabled", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter } = loaded;

  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const logActions = [];

  AuditService.logAction = async (entry) => {
    logActions.push(entry);
  };
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async () => {};

  t.after(() => {
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.getNodeDispatcher = async () => async () => ({ output: "ok" });
  adapter.agents = new Map([
    [
      "node-agent",
      {
        id: "node-agent",
        name: "Node Agent",
        role: "test",
        runtime: "node",
        allowedScopes: ["scope:execute"],
        capabilities: ["node_execution", "reasoning"],
        enable_reasoning: true
      }
    ]
  ]);

  await adapter.executeAgent("node-agent", "user-1", { tenant_id: "tenant-1", input: "x" }, ["scope:execute"], "tenant-1");

  assert.equal(logActions.length, 1);
  assert.equal(logActions[0].action, "EXECUTE_NODE_WITH_REASONING");
  assert.equal(logActions[0].payload.reasoning_enabled, true);
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

test("UnifiedAgentAdapter reports CONFIG_NOT_FOUND when node dispatcher module is unavailable", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter, NodeExecutionDispatchError } = loaded;

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
    ],
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

  for (const agentId of ["node-agent", "hybrid-agent"]) {
    await assert.rejects(
      () =>
        adapter.executeAgent(
          agentId,
          "user-1",
          {
            tenant_id: "tenant-1",
            input: "dispatch from missing module",
            metadata: { trace_id: `${agentId}-missing-runner` }
          },
          ["scope:execute"],
          "tenant-1"
        ),
      (error) => {
        assert.equal(error instanceof NodeExecutionDispatchError, true);
        assert.equal(error.code, "CONFIG_NOT_FOUND");
        assert.equal(error.classification, "CONFIG_FAILURE");
        return true;
      }
    );
  }

  assert.equal(taskUpdates.length, 2);
  for (const update of taskUpdates) {
    assert.equal(update[1], "FAILED");
    assert.match(update[2].error, /^CONFIG_NOT_FOUND:/);
  }
});

test("UnifiedAgentAdapter keeps transitive ERR_MODULE_NOT_FOUND as runtime failure", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;
  const { UnifiedAgentAdapter, NodeExecutionDispatchError } = loaded;

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
  adapter.getNodeDispatcher = async () => {
    const error = new Error("Cannot find package 'left-pad' imported from /workspace/src/runners/agentRunner.js");
    error.code = "ERR_MODULE_NOT_FOUND";
    throw error;
  };
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
          input: "dispatch through transitive missing dependency",
          metadata: { trace_id: "node-agent-missing-transitive" }
        },
        ["scope:execute"],
        "tenant-1"
      ),
    (error) => {
      assert.equal(error instanceof NodeExecutionDispatchError, true);
      assert.equal(error.code, "RUNTIME_FAILURE");
      assert.equal(error.classification, "RUNTIME_FAILURE");
      assert.match(error.message, /^RUNTIME_FAILURE: Node runtime execution failed for agent node-agent:/);
      return true;
    }
  );

  assert.equal(taskUpdates.length, 1);
  assert.equal(taskUpdates[0][1], "FAILED");
  assert.match(taskUpdates[0][2].error, /^RUNTIME_FAILURE:/);
  assert.equal(taskUpdates[0][2].blocker, "RUNTIME_FAILURE");
});
