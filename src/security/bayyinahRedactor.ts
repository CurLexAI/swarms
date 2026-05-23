export type RiskLevel = "low" | "medium" | "high";

export interface RedactionFinding {
  type: "saudi_national_id" | "email" | "phone" | "iban" | "commercial_registration" | "name_placeholder" | "money";
  match: string;
  replacement: string;
}

export interface RedactionResult {
  sanitizedText: string;
  findings: RedactionFinding[];
  riskLevel: RiskLevel;
}

const DETECTORS: Array<{ type: RedactionFinding["type"]; regex: RegExp; replacement: string }> = [
  { type: "commercial_registration", regex: /\bCR[-\s:]?\d{10}\b/gi, replacement: "[REDACTED_CR_NUMBER]" },
  { type: "saudi_national_id", regex: /\b[12]\d{9}\b/g, replacement: "[REDACTED_SA_NATIONAL_ID]" },
  { type: "email", regex: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g, replacement: "[REDACTED_EMAIL]" },
  { type: "phone", regex: /(?:\+966|0)5\d{8}\b/g, replacement: "[REDACTED_PHONE]" },
  { type: "iban", regex: /\bSA\d{2}[A-Z0-9]{2}\d{18}\b/g, replacement: "[REDACTED_IBAN]" },
  { type: "name_placeholder", regex: /\b(?:NAME|CLIENT_NAME|FULL_NAME|CUSTOMER_NAME|الاسم|اسم العميل)\b/gi, replacement: "[REDACTED_NAME]" },
  { type: "money", regex: /\b(?:SAR|ريال|USD|\$)\s?\d{1,3}(?:[,\s]?\d{3})*(?:\.\d{1,2})?\b/g, replacement: "[REDACTED_MONEY]" }
];

export function redactSensitiveText(input: string): RedactionResult {
  let sanitizedText = input;
  const findings: RedactionFinding[] = [];

  for (const detector of DETECTORS) {
    const matches = [...sanitizedText.matchAll(detector.regex)];
    if (matches.length === 0) {
      continue;
    }

    for (const match of matches) {
      findings.push({
        type: detector.type,
        match: match[0],
        replacement: detector.replacement
      });
    }

    sanitizedText = sanitizedText.replace(detector.regex, detector.replacement);
  }

  const uniqueTypes = new Set(findings.map((finding) => finding.type));
  const riskLevel: RiskLevel = findings.length === 0
    ? "low"
    : uniqueTypes.has("saudi_national_id") || uniqueTypes.has("iban")
      ? "high"
      : "medium";

  return { sanitizedText, findings, riskLevel };
}
