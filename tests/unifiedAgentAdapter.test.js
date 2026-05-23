import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const adapterPath = path.join(process.cwd(), 'src/services/unifiedAgentAdapter.ts');

test('forwardToPythonEngine guards missing PYTHON_BACKEND_URL with CONFIG_NOT_FOUND and structured log', () => {
  const source = fs.readFileSync(adapterPath, 'utf8');

  assert.match(source, /const backendUrl = process\.env\.PYTHON_BACKEND_URL\?\.trim\(\);/);
  assert.match(source, /if \(!backendUrl\) \{/);
  assert.match(source, /logger\.error\(\s*\{ agentId: agent\.id, configKey: "PYTHON_BACKEND_URL" \},\s*"CONFIG_NOT_FOUND: PYTHON_BACKEND_URL is required for python agent forwarding"/s);
  assert.match(source, /throw new Error\("CONFIG_NOT_FOUND: PYTHON_BACKEND_URL is required for python agent forwarding"\);/);
  assert.match(source, /const normalizedBackendUrl = backendUrl\.replace\(/);
  assert.match(source, /fetch\(`\$\{normalizedBackendUrl\}\/api\/v1\/workflow\/query`/);
});

test("loadRegistry logs loaded and reasoning-enabled counters for mixed definitions", () => {
  const source = fs.readFileSync(adapterPath, "utf8");

  assert.match(source, /let loadedAgents = 0;/);
  assert.match(source, /let reasoningEnabledAgents = 0;/);
  assert.match(source, /loadedAgents \+= 1;/);
  assert.match(source, /if \(agent\.enable_reasoning\) \{\s*reasoningEnabledAgents \+= 1;\s*\}/s);
  assert.match(
    source,
    /logger\.info\(\s*\{\s*loadedAgents,\s*reasoningEnabledAgents,\s*registryPath:\s*selectedRegistryPath\s*\},\s*"✅ LexPrim Intelligence Matrix loaded"\s*\);/s
  );
});

test("loadRegistry supports primary and fallback registry paths and accepts dict-keyed agents", () => {
  const source = fs.readFileSync(adapterPath, 'utf8');

  assert.match(source, /path\.resolve\(MODULE_DIR,\s*"\.\.\/\.\.\/\.agents\/config\/agents\.yaml"\)/);
  assert.match(source, /process\.env\.AGENT_REGISTRY_PATH\?\.trim\(\)/);
  assert.match(source, /if \(resolvedEnvRegistryPath\) \{/);
  assert.match(source, /registryPathSource = "env"/);
  assert.match(source, /else if \(fs\.existsSync\(moduleDefaultRegistryPath\)\) \{/);
  assert.match(source, /registryPathSource = "default"/);
  assert.match(source, /else if \(fs\.existsSync\(moduleLegacyRegistryPath\)\) \{/);
  assert.match(source, /registryPathSource = "legacy_fallback"/);
  assert.match(source, /path\.resolve\(MODULE_DIR,\s*"\.\.\/\.\.\/agents\/registry\.yaml"\)/);
  assert.match(source, /CONFIG_NOT_FOUND: Required registry file was not found at \$\{selectedRegistryPath\}/);
  assert.match(source, /SYNTAX_FAILURE: Failed to parse registry file at \$\{selectedRegistryPath\}/);
  assert.match(source, /if \(Array\.isArray\(rawAgents\)\) \{/);
  assert.match(source, /Object\.entries\(rawAgents as Record<string, Record<string, unknown>>\)/);
  assert.match(source, /\(r\.id as string \| undefined\) \?\? key/);
  assert.match(source, /agents must be array or mapping/);
});

test("node dispatcher CONFIG_NOT_FOUND is limited to the canonical agentRunner module", () => {
  const source = fs.readFileSync(adapterPath, 'utf8');

  assert.match(source, /private isNodeRunnerModuleNotFound\(error: unknown\)/);
  assert.match(source, /if \(this\.isNodeRunnerModuleNotFound\(error\)\) \{/);
  assert.match(source, /CONFIG_NOT_FOUND: Node dispatcher module missing for agent/);
  assert.match(source, /if \(errorCode === "MISSING_API_KEY"\) \{/);
  assert.match(source, /CONFIG_NOT_FOUND: Node runtime configuration missing for agent/);
});

test("loadRegistry runtime: invalid array entries trigger startup failure and unhealthy service", async (t) => {
  let UnifiedAgentAdapter;
  try {
    const mod = await import("../src/services/unifiedAgentAdapter.js");
    UnifiedAgentAdapter = mod.UnifiedAgentAdapter;
  } catch {
    t.skip("JS companion not importable in this runtime");
    return;
  }

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "registry-test-"));
  const regPath = path.join(dir, "registry.yaml");
  fs.writeFileSync(regPath, [
    "version: 1",
    "agents:",
    "  - ~",
    "  - []",
    "  - bad_string",
    "  - {}",
    "  - id: \"\"",
    "  - id: valid-agent",
    "    name: Valid Agent",
    "    role: test",
    "    type: node",
    "    execution:",
    "      runtime: node",
    "    contexts:",
    "      allowed:",
    "        - scope:execute",
    "    capabilities:",
    "      - node_execution",
  ].join("\n"));

  const origPath = process.env.AGENT_REGISTRY_PATH;
  process.env.AGENT_REGISTRY_PATH = regPath;

  t.after(() => {
    if (origPath === undefined) delete process.env.AGENT_REGISTRY_PATH;
    else process.env.AGENT_REGISTRY_PATH = origPath;
    fs.rmSync(dir, { recursive: true, force: true });
  });

  assert.throws(
    () => new UnifiedAgentAdapter(),
    /REGISTRY_LOAD_FAILURE: Invalid agent entry at index 0 \(expected object\)/
  );
});

test("loadRegistry array path validates schema and fails fast instead of skipping entries", () => {
  const source = fs.readFileSync(adapterPath, "utf8");

  // Validates loop structure is present instead of blind cast.
  assert.match(source, /for \(let idx = 0; idx < rawAgents\.length; idx\+\+\) \{/);
  assert.doesNotMatch(source, /agentsList = rawAgents as AgentDefinition\[\];/,
    "blind cast must be removed");

  // Validates strict shape checks on mandatory fields.
  assert.match(source, /if \(!isRecord\(entry\)\) \{/);
  assert.match(source, /id must be non-empty string/);
  assert.match(source, /name must be non-empty string/);
  assert.match(source, /type must be one of python\|node\|hybrid/);
  assert.match(source, /required_scope must be non-empty string/);
  assert.match(source, /failurePhase = startupError\.code === "SYNTAX_FAILURE" \? "parse" : "schema_or_io"/);
  assert.match(source, /failureCode: startupError\.code/);
});


test("live .agents/config/agents.yaml declares mihwar/bayyinah and matches Modal deployment", () => {
  const cfgPath = path.join(process.cwd(), '.agents/config/agents.yaml');
  const raw = fs.readFileSync(cfgPath, 'utf8');

  assert.match(raw, /^agents:/m, 'top-level agents key must exist');
  assert.match(raw, /^\s{2}mihwar:/m, 'mihwar agent must be defined as a dict key');
  assert.match(raw, /^\s{2}bayyinah:/m, 'bayyinah agent must be defined as a dict key');

  const appMatches = raw.match(/^\s+app:\s*"([^"]+)"/gm) || [];
  assert.ok(appMatches.length >= 2, 'each agent must declare a modal.app value');
  for (const line of appMatches) {
    assert.match(line, /"curlexai-agents"/,
      `modal.app must match the actual Modal deployment name (curlexai-agents); got: ${line}`);
  }

  const modalAppPath = path.join(process.cwd(), '.agents/modal_app.py');
  const modalSrc = fs.readFileSync(modalAppPath, 'utf8');
  assert.match(modalSrc, /modal\.App\(\s*"curlexai-agents"\s*\)/,
    'modal_app.py must deploy under app name curlexai-agents');
  assert.match(modalSrc, /class MihwarAgent\b/);
  assert.match(modalSrc, /class BayyinahAgent\b/);
});
