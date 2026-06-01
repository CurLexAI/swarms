import test from 'node:test';
import assert from 'node:assert/strict';
import { buildContentSecurityPolicy } from '../src/security/contentSecurityPolicy.ts';

test('CSP connect-src allows self and backend API origin only', () => {
  const csp = buildContentSecurityPolicy('https://api.example.com/v1');
  assert.match(csp, /connect-src 'self' https:\/\/api\.example\.com/);
  assert.ok(!csp.includes('.modal.run'));
});
