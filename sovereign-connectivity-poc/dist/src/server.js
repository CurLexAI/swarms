import Fastify from 'fastify';
import { decide } from '@poc/policy/src/index';
import { decisionSchema, sha256, telemetrySchema } from '@poc/shared/src/index';
const deviceStore = new Map();
const auditLog = [];
const appendAudit = (kind, payload) => {
    const hashPrev = auditLog.length === 0 ? 'GENESIS' : auditLog[auditLog.length - 1].hashCurrent;
    const timestamp = new Date().toISOString();
    const hashCurrent = sha256(JSON.stringify({ kind, payload, timestamp, hashPrev }));
    const entry = { kind, payload, timestamp, hashPrev, hashCurrent };
    auditLog.push(entry);
    return entry;
};
export const buildServer = () => {
    const app = Fastify({ logger: true, https: undefined }); // mTLS-ready placeholder
    app.post('/telemetry', async (request, reply) => {
        const parsed = telemetrySchema.safeParse(request.body);
        if (!parsed.success)
            return reply.code(400).send({ error: parsed.error.issues });
        const decision = decide(parsed.data);
        deviceStore.set(parsed.data.deviceId, { telemetry: parsed.data, decision });
        appendAudit('telemetry', parsed.data);
        appendAudit('decision', decision);
        return { decision };
    });
    app.post('/decision', async (request, reply) => {
        const parsed = telemetrySchema.safeParse(request.body);
        if (!parsed.success)
            return reply.code(400).send({ error: parsed.error.issues });
        const decision = decide(parsed.data);
        const validDecision = decisionSchema.parse(decision);
        appendAudit('decision', validDecision);
        return { decision: validDecision };
    });
    app.get('/devices/:id/status', async (request, reply) => {
        const id = request.params.id;
        const status = deviceStore.get(id);
        if (!status)
            return reply.code(404).send({ error: 'device_not_found' });
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
