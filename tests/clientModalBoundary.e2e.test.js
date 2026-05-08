import test from 'node:test';
import assert from 'node:assert/strict';

import { callLocalAgentRelay } from '../src/runners/clientAgentRelay.ts';

test('browser-facing client relay only calls local /api/agent-relay (no modal domains)', async () => {
  const calls = [];
  const originalFetch = global.fetch;
  global.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } });
  };

  try {
    await callLocalAgentRelay({ agent_id: 'a', tenant_id: 't', input: 'q' });
  } finally {
    global.fetch = originalFetch;
  }

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/agent-relay');
  assert.ok(!calls[0].url.includes('.modal.run'));
});
