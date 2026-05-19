import Fastify from 'fastify';
import { decide } from '../../../packages/policy/src/index.js';
import { decisionSchema, sha256, telemetrySchema, type Decision, type DeviceTelemetry } from '../../../packages/shared/src/index.js';

type AuditEntry = { kind: 'telemetry' | 'decision' | 'action'; payload: object; timestamp: string; hashPrev: string; hashCurrent: string };
const deviceStore = new Map<string, { telemetry: DeviceTelemetry; decision: Decision }>();
const auditLog: AuditEntry[] = [];

const appendAudit = (kind: AuditEntry['kind'], payload: object): AuditEntry => {
  const hashPrev = auditLog.length === 0 ? 'GENESIS' : auditLog[auditLog.length - 1]!.hashCurrent;
  const timestamp = new Date().toISOString();
  const hashCurrent = sha256(JSON.stringify({ kind, payload, timestamp, hashPrev }));
  const entry: AuditEntry = { kind, payload, timestamp, hashPrev, hashCurrent };
  auditLog.push(entry);
  return entry;
};

export const buildServer = () => {
  const app = Fastify({ logger: true }); // mTLS-ready placeholder

  app.post('/telemetry', async (request, reply) => {
    const parsed = telemetrySchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: parsed.error.issues });
    const decision = decide(parsed.data);
    deviceStore.set(parsed.data.deviceId, { telemetry: parsed.data, decision });
    appendAudit('telemetry', parsed.data);
    appendAudit('decision', decision);
    return { decision };
  });

  app.post('/decision', async (request, reply) => {
    const parsed = telemetrySchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ error: parsed.error.issues });
    const decision = decide(parsed.data);
    const validDecision = decisionSchema.parse(decision);
    appendAudit('decision', validDecision);
    return { decision: validDecision };
  });

  app.get('/devices/:id/status', async (request, reply) => {
    const id = (request.params as { id: string }).id;
    const status = deviceStore.get(id);
    if (!status) return reply.code(404).send({ error: 'device_not_found' });
    return status;
  });

  app.get('/audit', async () => ({ entries: auditLog }));

  return app;
};

if (process.env.NODE_ENV !== 'test') {
  buildServer().listen({ port: 3000, host: '0.0.0.0' }).catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
