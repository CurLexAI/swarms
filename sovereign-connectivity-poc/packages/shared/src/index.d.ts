import { z } from 'zod';
export type Result<T, E> = {
    ok: true;
    value: T;
} | {
    ok: false;
    error: E;
};
export declare const telemetrySchema: z.ZodObject<{
    deviceId: z.ZodString;
    country: z.ZodString;
    signal: z.ZodObject<{
        rsrp: z.ZodNumber;
        rsrq: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        rsrp: number;
        rsrq: number;
    }, {
        rsrp: number;
        rsrq: number;
    }>;
    network: z.ZodObject<{
        operator: z.ZodString;
        rat: z.ZodEnum<["4G", "5G"]>;
    }, "strip", z.ZodTypeAny, {
        operator: string;
        rat: "4G" | "5G";
    }, {
        operator: string;
        rat: "4G" | "5G";
    }>;
    observedAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    deviceId: string;
    country: string;
    signal: {
        rsrp: number;
        rsrq: number;
    };
    network: {
        operator: string;
        rat: "4G" | "5G";
    };
    observedAt: string;
}, {
    deviceId: string;
    country: string;
    signal: {
        rsrp: number;
        rsrq: number;
    };
    network: {
        operator: string;
        rat: "4G" | "5G";
    };
    observedAt: string;
}>;
export type DeviceTelemetry = z.infer<typeof telemetrySchema>;
export declare const actionSchema: z.ZodEnum<["allow", "switch_apn", "quarantine", "telemetry_only"]>;
export type DecisionAction = z.infer<typeof actionSchema>;
export declare const decisionSchema: z.ZodObject<{
    decisionId: z.ZodString;
    action: z.ZodEnum<["allow", "switch_apn", "quarantine", "telemetry_only"]>;
    reason: z.ZodString;
    riskLevel: z.ZodEnum<["low", "medium", "high"]>;
    timestamp: z.ZodString;
}, "strip", z.ZodTypeAny, {
    decisionId: string;
    action: "allow" | "switch_apn" | "quarantine" | "telemetry_only";
    reason: string;
    riskLevel: "low" | "medium" | "high";
    timestamp: string;
}, {
    decisionId: string;
    action: "allow" | "switch_apn" | "quarantine" | "telemetry_only";
    reason: string;
    riskLevel: "low" | "medium" | "high";
    timestamp: string;
}>;
export type Decision = z.infer<typeof decisionSchema>;
export declare const sha256: (input: string) => string;
