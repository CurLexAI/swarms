import test from "node:test";
import assert from "node:assert/strict";
import { redactSensitiveText } from "../src/security/bayyinahRedactor.ts";

test("redacts sensitive entities and returns high risk", () => {
  const input = "ID 1234567890 email a@b.com phone +966512345678 iban SA0380000000608010167519 CR 1010123456 SAR 1,250 NAME";
  const result = redactSensitiveText(input);

  assert.equal(result.riskLevel, "high");
  assert.match(result.sanitizedText, /REDACTED_SA_NATIONAL_ID/);
  assert.match(result.sanitizedText, /REDACTED_EMAIL/);
  assert.match(result.sanitizedText, /REDACTED_PHONE/);
  assert.match(result.sanitizedText, /REDACTED_IBAN/);
  assert.match(result.sanitizedText, /REDACTED_CR_NUMBER/);
  assert.match(result.sanitizedText, /REDACTED_MONEY/);
  assert.match(result.sanitizedText, /REDACTED_NAME/);
  assert.ok(result.findings.length >= 7);
});

test("returns low risk when no matches", () => {
  const result = redactSensitiveText("general guidance text");
  assert.equal(result.riskLevel, "low");
  assert.equal(result.findings.length, 0);
});
