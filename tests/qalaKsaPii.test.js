import test from "node:test";
import assert from "node:assert/strict";

import {
  detectKsaPii,
  hasKsaPii,
  redactKsaPii,
} from "../src/security/qalaKsaPii.js";

test("national id is detected with leading 1", () => {
  const hits = detectKsaPii("الهوية: 1234567890");
  assert.equal(hits.length, 1);
  assert.equal(hits[0].category, "KSA_NATIONAL_ID");
  assert.equal(hits[0].maskedValue, "12…90");
});

test("iqama is detected with leading 2", () => {
  const hits = detectKsaPii("Iqama: 2345678901");
  assert.equal(hits[0].category, "KSA_IQAMA");
});

test("commercial registration is detected with leading 7", () => {
  const hits = detectKsaPii("CR No. 7012345678");
  assert.equal(hits[0].category, "KSA_COMMERCIAL_REGISTRATION");
});

test("iban is detected", () => {
  const hits = detectKsaPii("IBAN SA4420000001234567891234.");
  assert.equal(hits.length, 1);
  assert.equal(hits[0].category, "KSA_IBAN");
  assert.ok(hits[0].maskedValue.startsWith("SA"));
});

test("mobile +966 is detected", () => {
  const hits = detectKsaPii("Mobile: +966512345678");
  assert.equal(hits[0].category, "KSA_MOBILE");
});

test("mobile 966 (no plus) is detected", () => {
  const hits = detectKsaPii("Mobile: 966512345678");
  assert.equal(hits[0].category, "KSA_MOBILE");
});

test("mobile 05 (local) is detected", () => {
  const hits = detectKsaPii("Mobile: 0512345678");
  assert.equal(hits[0].category, "KSA_MOBILE");
});

test("ambiguous 10-digit ID (leading 5) is classified as ambiguous", () => {
  const hits = detectKsaPii("ID: 5123456789");
  assert.equal(hits[0].category, "KSA_ID_AMBIGUOUS_10DIGIT");
});

test("raw value never appears in masked output", () => {
  const raw = "1234567890";
  const hits = detectKsaPii(`X ${raw} Y`);
  assert.ok(!hits[0].maskedValue.includes(raw));
  assert.ok(hits[0].maskedValue.includes("…"));
});

test("redactKsaPii replaces raw value", () => {
  const text = "Patient national id 1234567890 was processed.";
  const redacted = redactKsaPii(text);
  assert.ok(!redacted.includes("1234567890"));
  assert.ok(redacted.includes("[KSA_NATIONAL_ID:12…90]"));
});

test("redactKsaPii preserves non-pii text", () => {
  assert.equal(redactKsaPii("Hello world."), "Hello world.");
});

test("11-digit number does NOT match as 10-digit id", () => {
  const hits = detectKsaPii("Number 12345678901");
  const idHits = hits.filter((h) => h.category === "KSA_NATIONAL_ID");
  assert.equal(idHits.length, 0);
});

test("IBAN does not double-match as 10-digit id", () => {
  const hits = detectKsaPii("SA4420000001234567891234");
  const cats = new Set(hits.map((h) => h.category));
  assert.deepEqual(cats, new Set(["KSA_IBAN"]));
});

test("short digit run does not match", () => {
  assert.deepEqual(detectKsaPii("Number 12345"), []);
});

test("IBAN + national id co-exist in same text", () => {
  const hits = detectKsaPii(
    "IBAN: SA4420000001234567891234 and ID 1234567890",
  );
  const cats = hits.map((h) => h.category);
  assert.ok(cats.includes("KSA_IBAN"));
  assert.ok(cats.includes("KSA_NATIONAL_ID"));
});

test("mobile + national id co-exist", () => {
  const hits = detectKsaPii("Mobile +966512345678 and ID 1234567890.");
  const cats = hits.map((h) => h.category);
  assert.ok(cats.includes("KSA_MOBILE"));
  assert.ok(cats.includes("KSA_NATIONAL_ID"));
  assert.equal(hits.length, 2);
});

test("empty string returns empty array", () => {
  assert.deepEqual(detectKsaPii(""), []);
  assert.equal(hasKsaPii(""), false);
});

test("non-string returns empty array", () => {
  assert.deepEqual(detectKsaPii(null), []);
  assert.deepEqual(detectKsaPii(12345), []);
});

test("no-pii text returns false", () => {
  assert.equal(hasKsaPii("This is benign text."), false);
});

test("has_ksa_pii truthy for iqama", () => {
  assert.equal(hasKsaPii("Iqama 2345678901."), true);
});
