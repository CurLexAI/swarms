import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
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
    /logger\.info\(\s*\{\s*loadedAgents,\s*reasoningEnabledAgents\s*\},\s*"✅ LexPrim Intelligence Matrix loaded"\s*\);/s
  );
});
