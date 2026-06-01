import { randomUUID } from 'node:crypto';
import { sha256, telemetrySchema, type DecisionAction, type DeviceTelemetry } from '../../../packages/shared/src/index.js';

interface CellularAdapter { collect(): Promise<DeviceTelemetry>; }
class MockCellularAdapter implements CellularAdapter {
  async collect(): Promise<DeviceTelemetry> {
    return telemetrySchema.parse({
      deviceId: 'win-agent-01', country: 'SA',
      signal: { rsrp: -120, rsrq: -18 },
      network: { operator: 'MockTel', rat: '5G' },
      observedAt: new Date().toISOString()
    });
  }
}

type AuditRow = { event: string; payload: object; hashPrev: string; hashCurrent: string; timestamp: string };
const log: AuditRow[] = [];
const append = (event: string, payload: object): void => {
  const hashPrev = log.length ? log[log.length - 1]!.hashCurrent : 'GENESIS';
  const timestamp = new Date().toISOString();
  const hashCurrent = sha256(JSON.stringify({ event, payload, hashPrev, timestamp }));
  log.push({ event, payload, hashPrev, hashCurrent, timestamp });
};

const executeAction = async (action: DecisionAction): Promise<string> => {
  if (action === 'allow') return 'allowed';
  if (action === 'switch_apn') return 'apn_switched_mock';
  if (action === 'quarantine') return 'network_quarantined_mock';
  return 'telemetry_logged_only';
};

const run = async (): Promise<void> => {
  const adapter: CellularAdapter = new MockCellularAdapter();
  const telemetry = await adapter.collect();
  append('telemetry_received', telemetry);

  const response = await fetch('http://localhost:3000/telemetry', {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(telemetry)
  });
  if (!response.ok) throw new Error(`telemetry_error_${response.status}`);
  const body = (await response.json()) as { decision: { action: DecisionAction } };

  append('decision_issued', body.decision);
  const executionId = randomUUID();
  const outcome = await executeAction(body.decision.action);
  append('action_executed', { executionId, action: body.decision.action, outcome });

  console.log(JSON.stringify({ telemetry, decision: body.decision, outcome, audit: log }, null, 2));
};

if (process.argv.includes('--demo')) {
  run().catch((error: unknown) => {
    console.error(error);
    process.exit(1);
  });
}
