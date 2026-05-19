import { describe, it, expect } from 'vitest';
import { telemetrySchema, sha256 } from '../packages/shared/src/index';
import { decide } from '../packages/policy/src/index';
import { buildServer } from '../apps/api/src/server';

describe('validation', () => {
  it('accepts telemetry schema', () => {
    const parsed = telemetrySchema.safeParse({ deviceId:'d1', country:'SA', signal:{rsrp:-100, rsrq:-10}, network:{operator:'op', rat:'4G'}, observedAt:new Date().toISOString() });
    expect(parsed.success).toBe(true);
  });
});

describe('policy', () => {
  it('quarantines non SA', () => {
    const d = decide({ deviceId:'d1', country:'US', signal:{rsrp:-80, rsrq:-10}, network:{operator:'op', rat:'5G'}, observedAt:new Date().toISOString() });
    expect(d.action).toBe('quarantine');
  });
});

describe('hash chain', () => {
  it('produces deterministic hashes', () => {
    const h1 = sha256('a'); const h2 = sha256('a');
    expect(h1).toEqual(h2);
  });
});

describe('api', () => {
  it('handles telemetry and status', async () => {
    const app = buildServer();
    const payload = { deviceId:'d9', country:'SA', signal:{rsrp:-120, rsrq:-12}, network:{operator:'op', rat:'5G'}, observedAt:new Date().toISOString() };
    const res = await app.inject({ method:'POST', url:'/telemetry', payload });
    expect(res.statusCode).toBe(200);
    const status = await app.inject({ method:'GET', url:'/devices/d9/status' });
    expect(status.statusCode).toBe(200);
    await app.close();
  });
});
