export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type PolicyDecision =
  | {
      allowed: true;
      riskLevel: RiskLevel;
      reason: string;
      sanitizedText: string;
    }
  | {
      allowed: false;
      riskLevel: RiskLevel;
      reason: string;
    };

const SECRET_PATTERNS: RegExp[] = [
  /sk-(proj|admin)?-[A-Za-z0-9_-]{20,}/,
  /sk-ant-api\d{2}-[A-Za-z0-9_-]{20,}/,
  /gh[pousr]_[A-Za-z0-9_]{20,}/,
  /github_pat_[A-Za-z0-9_]{20,}/,
  /AIza[0-9A-Za-z_-]{20,}/,
  /xai-[A-Za-z0-9_-]{20,}/,
  /gsk_[A-Za-z0-9_-]{20,}/,
  /pplx-[A-Za-z0-9_-]{20,}/,
  /\d{8,12}:[A-Za-z0-9_-]{30,}/,
  /-----BEGIN (RSA |EC |OPENSSH |)?PRIVATE KEY-----/
];

const PROMPT_INJECTION_MARKERS: string[] = [
  'ignore previous instructions',
  'ignore all previous instructions',
  'system prompt',
  'developer message',
  'reveal your instructions',
  'print your hidden prompt',
  'bypass policy',
  'disable safety',
  'اتجاهل التعليمات السابقة',
  'اكشف التعليمات',
  'اطبع النظام'
];

const PDPL_HIGH_RISK_MARKERS: string[] = [
  'national id',
  'iqama',
  'passport',
  'iban',
  'medical',
  'health record',
  'criminal record',
  'الهوية الوطنية',
  'الإقامة',
  'جواز السفر',
  'الآيبان',
  'سجل صحي',
  'سجل جنائي'
];

export function evaluateMcpTextInput(input: unknown): PolicyDecision {
  const text = stringifyInput(input);
  if (text.length > 200_000) {
    return {
      allowed: false,
      riskLevel: 'HIGH',
      reason: 'Input too large for MCP policy gate'
    };
  }

  for (const pattern of SECRET_PATTERNS) {
    if (pattern.test(text)) {
      return {
        allowed: false,
        riskLevel: 'CRITICAL',
        reason: 'Input appears to contain secrets'
      };
    }
  }

  const lowered = text.toLowerCase();
  for (const marker of PROMPT_INJECTION_MARKERS) {
    if (lowered.includes(marker.toLowerCase())) {
      return {
        allowed: false,
        riskLevel: 'HIGH',
        reason: 'Prompt-injection marker detected'
      };
    }
  }

  for (const marker of PDPL_HIGH_RISK_MARKERS) {
    if (lowered.includes(marker.toLowerCase())) {
      return {
        allowed: false,
        riskLevel: 'HIGH',
        reason: 'Potential PDPL-sensitive data detected'
      };
    }
  }

  return {
    allowed: true,
    riskLevel: 'LOW',
    reason: 'Input passed MCP policy gate',
    sanitizedText: text
  };
}

function stringifyInput(input: unknown): string {
  if (typeof input === 'string') {
    return input;
  }

  try {
    return JSON.stringify(input);
  } catch {
    return String(input);
  }
}
