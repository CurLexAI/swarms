import test from 'node:test';
import assert from 'node:assert/strict';
import {
  QararSovereignClient,
  createDefaultQararSwarmsTools,
  routeProtocol,
  toUnifiedTransportEnvelope,
  validateQararSwarmsRequest,
  type HttpFetcher,
  type QararSwarmsRequest
} from '../src/swarms/index.ts';

const baseRequest = (overrides: Partial<QararSwarmsRequest> = {}): QararSwarmsRequest => ({
  traceId: 'trace-swarms-001',
  agentId: 'swarms.legal-reasoning-agent',
  taskType: 'LEGAL_REASONING',
  modelId: 'deepseek-r1-32b',
  architecture: 'DIRECT_TOOL_CALL',
  prompt: 'حلل الالتزام النظامي لهذه السياسة وفق سياق سعودي.',
  context: [
    {
      key: 'authority',
      value: 'SAMA'
    }
  ],
  dataContext: {
    traceId: 'trace-swarms-001',
    jurisdiction: 'KSA',
    environment: 'production',
    dataClass: 'INTERNAL',
    containsPII: false
  },
  ...overrides
});

test('validates model-to-task routing before Swarms execution', () => {
  const valid = validateQararSwarmsRequest(baseRequest());
  assert.equal(valid.ok, true);

  const invalid = validateQararSwarmsRequest(
    baseRequest({ modelId: 'allam-7b' })
  );
  assert.equal(invalid.ok, false);
  if (!invalid.ok) {
    assert.equal(invalid.error.code, 'MODEL_TASK_MISMATCH');
  }
});

test('routes regulated or PII-bearing calls to ANP', () => {
  const routed = routeProtocol(
    baseRequest({
      dataContext: {
        traceId: 'trace-swarms-002',
        jurisdiction: 'KSA',
        environment: 'production',
        dataClass: 'REGULATED',
        containsPII: true
      }
    })
  );

  assert.equal(routed.ok, true);
  if (routed.ok) {
    assert.equal(routed.value.protocol, 'ANP');
  }
});

test('routes local context calls to MCP', () => {
  const routed = routeProtocol(
    baseRequest({
      taskType: 'LOCAL_CONTEXT',
      modelId: 'allam-7b',
      agentId: 'swarms.local-context-agent'
    })
  );

  assert.equal(routed.ok, true);
  if (routed.ok) {
    assert.equal(routed.value.protocol, 'MCP');
  }
});

test('builds UTE envelope with KSA sovereign controls', () => {
  const envelope = toUnifiedTransportEnvelope(baseRequest());

  assert.equal(envelope.ok, true);
  if (envelope.ok) {
    assert.equal(envelope.value.schemaVersion, 'ute.v1');
    assert.equal(envelope.value.controls.jurisdiction, 'KSA');
    assert.equal(envelope.value.controls.auditRequired, true);
    assert.equal(envelope.value.controls.retention, 'append-only');
  }
});

test('QararSovereignClient posts UTE envelope and enforces output contract', async () => {
  const fetcher: HttpFetcher = async (_url, init) => {
    const raw = JSON.parse(init.body) as {
      readonly traceId: string;
      readonly protocol: string;
    };

    return {
      ok: true,
      status: 200,
      json: async () => ({
        text: `accepted:${raw.traceId}`,
        confidence: 0.91,
        protocol: raw.protocol,
        sources: [
          {
            sourceId: 'sama.synthetic-control',
            sourceType: 'REGULATION',
            hash: 'sha256:fixture'
          }
        ]
      }),
      text: async () => ''
    };
  };

  const client = new QararSovereignClient({
    baseUrl: 'https://qarar.internal',
    timeoutMs: 500,
    fetcher
  });

  const result = await client.complete(baseRequest());
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.value.text, 'accepted:trace-swarms-001');
    assert.equal(result.value.escalated, false);
    assert.equal(result.value.protocol, 'ACP');
  }
});

test('default tools expose legal, local context, and Arabic drafting routes', () => {
  const client = new QararSovereignClient({
    baseUrl: 'https://qarar.internal',
    timeoutMs: 500,
    fetcher: async () => ({
      ok: true,
      status: 200,
      json: async () => ({ text: 'ok', confidence: 0.9, sources: [] }),
      text: async () => ''
    })
  });

  const tools = createDefaultQararSwarmsTools(client);
  assert.deepEqual(
    tools.map((tool) => tool.name),
    ['qarar_legal_reasoning', 'qarar_local_context', 'qarar_arabic_drafting']
  );
});
