import { randomUUID } from 'node:crypto';
import { sha256, telemetrySchema } from '../../../packages/shared/src/index.js';
class MockCellularAdapter {
    async collect() {
        return telemetrySchema.parse({
            deviceId: 'win-agent-01', country: 'SA',
            signal: { rsrp: -120, rsrq: -18 },
            network: { operator: 'MockTel', rat: '5G' },
            observedAt: new Date().toISOString()
        });
    }
}
const log = [];
const append = (event, payload) => {
    const hashPrev = log.length ? log[log.length - 1].hashCurrent : 'GENESIS';
    const timestamp = new Date().toISOString();
    const hashCurrent = sha256(JSON.stringify({ event, payload, hashPrev, timestamp }));
    log.push({ event, payload, hashPrev, hashCurrent, timestamp });
};
const executeAction = async (action) => {
    if (action === 'allow')
        return 'allowed';
    if (action === 'switch_apn')
        return 'apn_switched_mock';
    if (action === 'quarantine')
        return 'network_quarantined_mock';
    return 'telemetry_logged_only';
};
const run = async () => {
    const adapter = new MockCellularAdapter();
    const telemetry = await adapter.collect();
    append('telemetry_received', telemetry);
    const response = await fetch('http://localhost:3000/telemetry', {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(telemetry)
    });
    if (!response.ok)
        throw new Error(`telemetry_error_${response.status}`);
    const body = (await response.json());
    append('decision_issued', body.decision);
    const executionId = randomUUID();
    const outcome = await executeAction(body.decision.action);
    append('action_executed', { executionId, action: body.decision.action, outcome });
    console.log(JSON.stringify({ telemetry, decision: body.decision, outcome, audit: log }, null, 2));
};
if (process.argv.includes('--demo')) {
    run().catch((error) => {
        console.error(error);
        process.exit(1);
    });
}
