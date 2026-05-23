import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";


const SOURCE_PATH = path.resolve("src/services/unifiedAgentAdapter.ts");

function configureAllowedPythonBackend(t, backendUrl = "https://python-backend.invalid") {
  const originalBackendUrl = process.env.PYTHON_BACKEND_URL;
  const originalAllowedHosts = process.env.PYTHON_BACKEND_ALLOWED_HOSTS;

  process.env.PYTHON_BACKEND_URL = backendUrl;
  process.env.PYTHON_BACKEND_ALLOWED_HOSTS = new URL(backendUrl).hostname;

  t.after(() => {
    if (originalBackendUrl === undefined) delete process.env.PYTHON_BACKEND_URL;
    else process.env.PYTHON_BACKEND_URL = originalBackendUrl;
    if (originalAllowedHosts === undefined) delete process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
    else process.env.PYTHON_BACKEND_ALLOWED_HOSTS = originalAllowedHosts;
  });
}

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
        allowedScopes: ["scope:execute"],
        capabilities: ["python_execution"]
      }
    ]
  ]);

  configureAllowedPythonBackend(t);

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
      assert.match(error.message, /RUNTIME_FAILURE: Python engine returned HTTP 500/i);
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
  assert.match(updateTaskStatusCalls[0][2].error, /RUNTIME_FAILURE: Python engine returned HTTP 500/i);
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
        allowedScopes: ["scope:execute"],
        capabilities: ["python_execution"]
      }
    ]
  ]);

  configureAllowedPythonBackend(t);

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
      assert.match(error.message, /RUNTIME_FAILURE: python engine request transport failure/i);
      assert.doesNotMatch(error.message, /ECONNREFUSED/i);
      assert.doesNotMatch(error.message, /python-backend\.internal/i);
      return true;
    }
  );

  assert.equal(updateTaskStatusCalls.length, 1);
  assert.equal(updateTaskStatusCalls[0][1], "FAILED");
  assert.match(updateTaskStatusCalls[0][2].error, /RUNTIME_FAILURE: python engine request transport failure/i);
  assert.doesNotMatch(updateTaskStatusCalls[0][2].error, /ECONNREFUSED|python-backend\.internal/i);
});

test("UnifiedAgentAdapter.executeAgent retries fetch failed errors with ENOTFOUND cause and keeps client errors sanitized", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalFetch = global.fetch;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const originalMaxAttempts = process.env.PYTHON_BACKEND_MAX_ATTEMPTS;

  const fetchCalls = [];
  const auditCalls = [];

  const makeErrnoError = (code) => {
    const err = new Error(`getaddrinfo ${code} python-backend.invalid`);
    err.code = code;
    return err;
  };

  global.fetch = async () => {
    fetchCalls.push(1);
    throw makeErrnoError("ENOTFOUND");
  };

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async (...args) => { auditCalls.push(args); };
  AuditService.updateTaskStatus = async () => {};

  process.env.PYTHON_BACKEND_URL = "http://python-backend.invalid";
  process.env.PYTHON_BACKEND_MAX_ATTEMPTS = "2";

  const updateTaskStatusCalls = [];
  let attempts = 0;

  global.fetch = async () => {
    attempts += 1;
    const cause = Object.assign(new Error("getaddrinfo ENOTFOUND python-backend.internal"), { code: "ENOTFOUND" });
    const err = new TypeError("fetch failed");
    err.cause = cause;
    throw err;
  };

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => updateTaskStatusCalls.push(args);

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
    if (originalMaxAttempts === undefined) delete process.env.PYTHON_BACKEND_MAX_ATTEMPTS;
    else process.env.PYTHON_BACKEND_MAX_ATTEMPTS = originalMaxAttempts;
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
        allowedScopes: ["scope:execute"],
        capabilities: ["python_execution"]
      }
    ]
  ]);

  await assert.rejects(
    async () =>
      adapter.executeAgent(
        "py-agent",
        "user-1",
        { tenant_id: "tenant-1", input: "run", metadata: { source: "integration-test" } },
        ["scope:execute"],
        "tenant-1"
      ),
    (error) => {
      assert.match(error.message, /RUNTIME_FAILURE: python engine (request transport failure|exhausted retry budget)/i);
      assert.doesNotMatch(error.message, /ENOTFOUND/i);
      assert.doesNotMatch(error.message, /python-backend\.invalid/i);
  });

  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);

  process.env.PYTHON_BACKEND_URL = "http://python-backend.invalid";
  process.env.PYTHON_BACKEND_MAX_ATTEMPTS = "2";

  await assert.rejects(
    () => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run" }, ["scope:execute"], "tenant-1"),
    (error) => {
      assert.match(error.message, /RUNTIME_FAILURE: python engine request transport failure/i);
      assert.doesNotMatch(error.message, /ENOTFOUND|python-backend|http|token/i);
      return true;
    }
  );

  assert.equal(fetchCalls.length, 2, "should have retried once (2 total attempts) for ENOTFOUND");
  const requestFailureAudit = auditCalls.find((a) => a[2] === "PYTHON_ENGINE_REQUEST_FAILURE");
  assert.ok(requestFailureAudit, "PYTHON_ENGINE_REQUEST_FAILURE audit event should have been logged");
  assert.equal(requestFailureAudit[3].error_code, "ENOTFOUND", "audit event should capture error_code");
  assert.equal(requestFailureAudit[3].error_name, "Error", "audit event should capture error_name");
  assert.equal(attempts, 2, "retryable ENOTFOUND cause should consume retry budget");
  assert.equal(updateTaskStatusCalls.length, 1);
});

test("UnifiedAgentAdapter.executeAgent retries fetch failed errors with ECONNREFUSED cause and keeps client errors sanitized", async (t) => {
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
  let attempts = 0;

  global.fetch = async () => {
    attempts += 1;
    if (attempts === 1) {
      const cause = Object.assign(new Error("connect ECONNREFUSED 10.1.2.3:8000"), { code: "ECONNREFUSED" });
      const err = new TypeError("fetch failed");
      err.cause = cause;
      throw err;
    }
    return {
      ok: true,
      status: 200,
      headers: { get: (name) => (name.toLowerCase() === "content-type" ? "application/json" : null) },
      json: async () => ({ output: "ok" })
    };
  };

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => updateTaskStatusCalls.push(args);

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);

  process.env.PYTHON_BACKEND_URL = "http://python-backend.invalid";
  process.env.PYTHON_BACKEND_MAX_ATTEMPTS = "2";

  const result = await adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run" }, ["scope:execute"], "tenant-1");
  assert.equal(result.status, "success");
  assert.equal(attempts, 2, "retryable ECONNREFUSED cause should retry once before success");
  assert.equal(updateTaskStatusCalls[0][1], "COMPLETED");
});

test("UnifiedAgentAdapter.executeAgent rejects successful non-JSON python responses with sanitized runtime error", async (t) => {
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
  let jsonCalled = false;

  global.fetch = async () => ({
    ok: true,
    status: 200,
    headers: {
      get: (name) => (name.toLowerCase() === "content-type" ? "text/html; charset=utf-8" : null)
    },
    text: async () => "<html>upstream maintenance page</html>",
    json: async () => {
      jsonCalled = true;
      return { hidden: true };
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
        allowedScopes: ["scope:execute"],
        capabilities: ["python_execution"]
      }
    ]
  ]);

  configureAllowedPythonBackend(t);

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
        "tenant-1"
      ),
    (error) => {
      assert.match(error.message, /Python engine request failed with status 200/);
      assert.match(error.message, /\(ref: [0-9a-f]{8}\)/i);
      return true;
    }
  );

  assert.equal(jsonCalled, false, "response.json() must not be called when content-type is not application/json");
  assert.equal(updateTaskStatusCalls.length, 1);
  assert.equal(updateTaskStatusCalls[0][1], "FAILED");
  assert.match(updateTaskStatusCalls[0][2].error, /Python engine request failed with status 200/);
});

test("UnifiedAgentAdapter.executeAgent retries retryable 503 responses up to PYTHON_BACKEND_MAX_ATTEMPTS total attempts", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalFetch = global.fetch;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const originalMaxAttempts = process.env.PYTHON_BACKEND_MAX_ATTEMPTS;

  const updateTaskStatusCalls = [];
  let fetchCalls = 0;
  global.fetch = async () => {
    fetchCalls += 1;
    return {
      ok: false,
      status: 503,
      text: async () => "temporarily unavailable"
    };
  };

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async (...args) => updateTaskStatusCalls.push(args);

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
    if (originalMaxAttempts === undefined) delete process.env.PYTHON_BACKEND_MAX_ATTEMPTS;
    else process.env.PYTHON_BACKEND_MAX_ATTEMPTS = originalMaxAttempts;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);
  configureAllowedPythonBackend(t);
  process.env.PYTHON_BACKEND_MAX_ATTEMPTS = "3";

  await assert.rejects(() => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run", metadata: {} }, ["scope:execute"], "tenant-1"));
  assert.equal(fetchCalls, 3);
  assert.equal(updateTaskStatusCalls.length, 1);
});

test("UnifiedAgentAdapter.executeAgent performs a single outbound attempt for retryable 503 when PYTHON_BACKEND_MAX_ATTEMPTS=1", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalFetch = global.fetch;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const originalMaxAttempts = process.env.PYTHON_BACKEND_MAX_ATTEMPTS;

  let fetchCalls = 0;
  global.fetch = async () => {
    fetchCalls += 1;
    return { ok: false, status: 503, text: async () => "temporarily unavailable" };
  };

  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async () => {};

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
    if (originalMaxAttempts === undefined) delete process.env.PYTHON_BACKEND_MAX_ATTEMPTS;
    else process.env.PYTHON_BACKEND_MAX_ATTEMPTS = originalMaxAttempts;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);
  configureAllowedPythonBackend(t);
  process.env.PYTHON_BACKEND_MAX_ATTEMPTS = "1";

  await assert.rejects(() => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run", metadata: {} }, ["scope:execute"], "tenant-1"));
  assert.equal(fetchCalls, 1);
});

test("UnifiedAgentAdapter.executeAgent blocks forwarding in strict mode when allowlist is empty", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;

  const originalFetch = global.fetch;
  const originalNodeEnv = process.env.NODE_ENV;
  const originalEnforceAllowlist = process.env.ENFORCE_BACKEND_ALLOWLIST;
  const originalAllowedHosts = process.env.PYTHON_BACKEND_ALLOWED_HOSTS;

  let fetchCalls = 0;
  global.fetch = async () => {
    fetchCalls += 1;
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => ({ output: "ok" }) };
  };

  t.after(() => {
    global.fetch = originalFetch;
    if (originalNodeEnv === undefined) delete process.env.NODE_ENV;
    else process.env.NODE_ENV = originalNodeEnv;
    if (originalEnforceAllowlist === undefined) delete process.env.ENFORCE_BACKEND_ALLOWLIST;
    else process.env.ENFORCE_BACKEND_ALLOWLIST = originalEnforceAllowlist;
    if (originalAllowedHosts === undefined) delete process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
    else process.env.PYTHON_BACKEND_ALLOWED_HOSTS = originalAllowedHosts;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);
  process.env.PYTHON_BACKEND_URL = "https://python-backend.example";
  process.env.ENFORCE_BACKEND_ALLOWLIST = "true";
  delete process.env.PYTHON_BACKEND_ALLOWED_HOSTS;

  await assert.rejects(() => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run", metadata: {} }, ["scope:execute"], "tenant-1"), /CONFIG_NOT_FOUND: PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled/);
  assert.equal(fetchCalls, 0);
});

test("UnifiedAgentAdapter.executeAgent blocks non-https backend URLs in strict mode", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const originalEnforceAllowlist = process.env.ENFORCE_BACKEND_ALLOWLIST;
  const originalAllowedHosts = process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
  const originalFetch = global.fetch;
  let fetchCalls = 0;
  global.fetch = async () => { fetchCalls += 1; throw new Error("unexpected fetch"); };

  t.after(() => {
    global.fetch = originalFetch;
    if (originalEnforceAllowlist === undefined) delete process.env.ENFORCE_BACKEND_ALLOWLIST;
    else process.env.ENFORCE_BACKEND_ALLOWLIST = originalEnforceAllowlist;
    if (originalAllowedHosts === undefined) delete process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
    else process.env.PYTHON_BACKEND_ALLOWED_HOSTS = originalAllowedHosts;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);
  process.env.PYTHON_BACKEND_URL = "http://python-backend.example";
  process.env.ENFORCE_BACKEND_ALLOWLIST = "true";
  process.env.PYTHON_BACKEND_ALLOWED_HOSTS = "python-backend.example";

  await assert.rejects(() => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run", metadata: {} }, ["scope:execute"], "tenant-1"), /CONFIG_NOT_FOUND: PYTHON_BACKEND_URL must use HTTPS/);
  assert.equal(fetchCalls, 0);
});

test("UnifiedAgentAdapter.executeAgent allows strict mode forwarding when host is allowlisted and https", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalEnforceAllowlist = process.env.ENFORCE_BACKEND_ALLOWLIST;
  const originalAllowedHosts = process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
  const originalFetch = global.fetch;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  let fetchCalls = 0;
  global.fetch = async () => {
    fetchCalls += 1;
    return { ok: true, status: 200, headers: { get: () => "application/json" }, json: async () => ({ output: "ok" }) };
  };
  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.updateTaskStatus = async () => {};

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
    if (originalEnforceAllowlist === undefined) delete process.env.ENFORCE_BACKEND_ALLOWLIST;
    else process.env.ENFORCE_BACKEND_ALLOWLIST = originalEnforceAllowlist;
    if (originalAllowedHosts === undefined) delete process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
    else process.env.PYTHON_BACKEND_ALLOWED_HOSTS = originalAllowedHosts;
  });

  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);
  process.env.PYTHON_BACKEND_URL = "https://python-backend.example";
  process.env.ENFORCE_BACKEND_ALLOWLIST = "true";
  process.env.PYTHON_BACKEND_ALLOWED_HOSTS = "python-backend.example";

  await assert.doesNotReject(() => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run", metadata: {} }, ["scope:execute"], "tenant-1"));
  assert.equal(fetchCalls, 1);
});

test("UnifiedAgentAdapter.executeAgent maps AbortError timeout to PYTHON_ENGINE_TIMEOUT and marks task FAILED", async (t) => {
  const loaded = await loadUnifiedAgentAdapterFromTs(t);
  if (!loaded) return;
  const { UnifiedAgentAdapter } = loaded;
  const AuditService = await loadAuditServiceOrSkip(t);
  if (!AuditService) return;

  const originalFetch = global.fetch;
  const originalBackendUrl = process.env.PYTHON_BACKEND_URL;
  const originalAllowedHosts = process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
  const originalLogAction = AuditService.logAction;
  const originalUpdateTaskStatus = AuditService.updateTaskStatus;
  const originalLogSecurityViolation = AuditService.logSecurityViolation;
  const originalCreateTask = AuditService.createTask;
  const taskUpdates = [];

  const abortError = Object.assign(new Error("The operation was aborted"), { name: "AbortError" });
  global.fetch = async () => { throw abortError; };
  AuditService.logAction = async () => {};
  AuditService.logSecurityViolation = async () => {};
  AuditService.createTask = async () => {};
  AuditService.updateTaskStatus = async (...args) => { taskUpdates.push(args); };

  t.after(() => {
    global.fetch = originalFetch;
    AuditService.logAction = originalLogAction;
    AuditService.updateTaskStatus = originalUpdateTaskStatus;
    AuditService.logSecurityViolation = originalLogSecurityViolation;
    AuditService.createTask = originalCreateTask;
    if (originalBackendUrl === undefined) delete process.env.PYTHON_BACKEND_URL;
    else process.env.PYTHON_BACKEND_URL = originalBackendUrl;
    if (originalAllowedHosts === undefined) delete process.env.PYTHON_BACKEND_ALLOWED_HOSTS;
    else process.env.PYTHON_BACKEND_ALLOWED_HOSTS = originalAllowedHosts;
  });

  process.env.PYTHON_BACKEND_URL = "https://python-backend.example";
  process.env.PYTHON_BACKEND_ALLOWED_HOSTS = "python-backend.example";
  const adapter = new UnifiedAgentAdapter();
  adapter.agents = new Map([["py-agent", { id: "py-agent", name: "Python Agent", role: "test", runtime: "python", allowedScopes: ["scope:execute"], capabilities: ["python_execution"] }]]);

  await assert.rejects(
    () => adapter.executeAgent("py-agent", "user-1", { tenant_id: "tenant-1", input: "run", metadata: {} }, ["scope:execute"], "tenant-1"),
    (err) => {
      assert.match(err.code ?? err.message, /PYTHON_ENGINE_TIMEOUT|timed out/i);
      return true;
    }
  );

  assert.equal(taskUpdates.length, 1);
  assert.equal(taskUpdates[0][1], "FAILED");
  assert.match(taskUpdates[0][2].blocker ?? taskUpdates[0][2].failure_class ?? "", /PYTHON_ENGINE_TIMEOUT/);
  const errorText = taskUpdates[0][2].error ?? "";
  assert.doesNotMatch(errorText, /password|token|secret|api.?key|bearer/i);
});
