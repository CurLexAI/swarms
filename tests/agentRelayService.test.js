import test from 'node:test';
import assert from 'node:assert/strict';
import { handleAgentRelayRequest } from '../src/services/agentRelayService.ts';

test('agent relay endpoint forwards server-to-server using env URL', async () => {
  process.env.MODAL_RELAY_UPSTREAM_URL = 'https://relay-backend.example';
  const originalFetch = global.fetch;
  const calls = [];
  global.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ output: 'ok' }), { status: 200, headers: { 'content-type': 'application/json' } });
  };

  try {
    const req = new Request('http://localhost/api/agent-relay', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ agent_id: 'x', tenant_id: 't', input: 'q' })
    });
    const res = await handleAgentRelayRequest(req);
    assert.equal(res.status, 200);
  } finally { global.fetch = originalFetch; }

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://relay-backend.example/api/v1/workflow/query');
});
