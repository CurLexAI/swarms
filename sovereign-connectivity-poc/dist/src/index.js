import { v4 as uuidv4 } from 'uuid';
export const decide = (telemetry) => {
    const timestamp = new Date().toISOString();
    if (telemetry.country !== 'SA') {
        return { decisionId: uuidv4(), action: 'quarantine', reason: 'Country خارج النطاق المسموح (SA).', riskLevel: 'high', timestamp };
    }
    if (telemetry.signal.rsrp < -115) {
        return { decisionId: uuidv4(), action: 'switch_apn', reason: 'ضعف إشارة شديد يتطلب APN بديل.', riskLevel: 'medium', timestamp };
    }
    return { decisionId: uuidv4(), action: 'allow', reason: 'الاتصال ضمن السياسة.', riskLevel: 'low', timestamp };
};
