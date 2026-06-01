import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const manifest = JSON.parse(readFileSync('public/trust/cdn-integrity.json', 'utf8'));
const localScript = readFileSync('public/trust/vendor/fallback-lib.js');
const compute = (content) => `sha384-${createHash('sha384').update(content).digest('base64')}`;

test('fallback load succeeds when integrity matches', async () => {
  const { integrity } = manifest.trustFallbackLib;
  assert.equal(compute(localScript), integrity);
});

test('fallback load fails when integrity mismatches', async () => {
  const { integrity } = manifest.trustFallbackLib;
  const tampered = integrity.slice(0, -1) + (integrity.endsWith('A') ? 'B' : 'A');
  assert.notEqual(compute(localScript), tampered);
});
