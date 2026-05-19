import { createHash } from 'node:crypto';
import { z } from 'zod';

export type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

export const telemetrySchema = z.object({
  deviceId: z.string().min(1),
  country: z.string().length(2),
  signal: z.object({ rsrp: z.number().min(-160).max(-40), rsrq: z.number().min(-40).max(0) }),
  network: z.object({ operator: z.string().min(1), rat: z.enum(['4G', '5G']) }),
  observedAt: z.string().datetime()
});

export type DeviceTelemetry = z.infer<typeof telemetrySchema>;

export const actionSchema = z.enum(['allow', 'switch_apn', 'quarantine', 'telemetry_only']);
export type DecisionAction = z.infer<typeof actionSchema>;

export const decisionSchema = z.object({
  decisionId: z.string().uuid(),
  action: actionSchema,
  reason: z.string().min(3),
  riskLevel: z.enum(['low', 'medium', 'high']),
  timestamp: z.string().datetime()
});
export type Decision = z.infer<typeof decisionSchema>;

export const sha256 = (input: string): string => createHash('sha256').update(input).digest('hex');
