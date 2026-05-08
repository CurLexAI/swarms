import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createInMemoryRateLimiter,
  detectReplay,
  toPublicError,
  toSanitizedLog,
  validateContactPayload
} from '../src/apiSecurity.js';

test('rejects malformed payload and unknown fields', () => {
  assert.equal(validateContactPayload(null).ok, false);
  const unknown = validateContactPayload({name:'A',email:'a@b.com',message:'0123456789',nonce:'123456789012',turnstileToken:'1234567890',extra:'x'});
  assert.equal(unknown.ok, false);
  assert.equal(unknown.reason, 'unknown_fields');
});

test('spam/rate limit blocks burst traffic', () => {
  const limiter = createInMemoryRateLimiter({ windowMs: 1000, limit: 2 });
  assert.equal(limiter('1.2.3.4').allowed, true);
  assert.equal(limiter('1.2.3.4').allowed, true);
  assert.equal(limiter('1.2.3.4').allowed, false);
});

test('replay nonce is rejected on second attempt', () => {
  const nonce = 'nonce-123456789012';
  assert.equal(detectReplay(nonce), false);
  assert.equal(detectReplay(nonce), true);
});

test('public errors are generic and logs are redacted', () => {
  assert.deepEqual(toPublicError(), { error: 'Request rejected. Please verify input and retry.' });
  const sanitized = toSanitizedLog(new Error('upstream token=abc123 failed'), { route:'/api/contact' });
  assert.match(sanitized.message, /token=\[REDACTED\]/);
  assert.equal(sanitized.context.route, '/api/contact');
});
