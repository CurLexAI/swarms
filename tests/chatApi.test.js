import test from 'node:test';
import assert from 'node:assert/strict';
import { handleChatApiRequest } from '../src/backend/chatApi.js';

const baseConfig = {
  environment: 'staging',
  allowedOrigins: { prod: ['https://app.example.com'], staging: ['https://staging.example.com'] },
  allowCredentials: false
};

test('GET /api/chat returns 405', () => {
  const res = handleChatApiRequest({ method: 'GET', headers: { origin: 'https://staging.example.com' } }, baseConfig);
  assert.equal(res.status, 405);
});

test('PUT /api/chat returns 405', () => {
  const res = handleChatApiRequest({ method: 'PUT', headers: { origin: 'https://staging.example.com' } }, baseConfig);
  assert.equal(res.status, 405);
});

test('OPTIONS /api/chat returns CORS policy with POST, OPTIONS only', () => {
  const res = handleChatApiRequest({ method: 'OPTIONS', headers: { origin: 'https://staging.example.com' } }, baseConfig);
  assert.equal(res.status, 204);
  assert.equal(res.headers['Access-Control-Allow-Methods'], 'POST, OPTIONS');
  assert.equal(res.headers['Access-Control-Allow-Origin'], 'https://staging.example.com');
  assert.equal(res.headers['Access-Control-Allow-Credentials'], undefined);
});

test('POST /api/chat from unauthorized origin is rejected', () => {
  const res = handleChatApiRequest({ method: 'POST', headers: { origin: 'https://evil.example.com' } }, baseConfig);
  assert.equal(res.status, 403);
});
