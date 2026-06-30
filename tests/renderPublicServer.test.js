import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { createPublicServer, getContentType, resolvePublicPath } from '../scripts/render/serve-public.mjs';

async function withServer(t, publicRoot) {
  const server = createPublicServer({ publicRoot });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => {
    server.closeAllConnections();
    server.close(resolve);
  }));
  const address = server.address();
  assert.equal(typeof address, 'object');
  return `http://127.0.0.1:${address.port}`;
}

test('SR.BSM public server exposes a no-secret health endpoint', async (t) => {
  const publicRoot = await mkdtemp(join(tmpdir(), 'sr-bsm-public-'));
  const baseUrl = await withServer(t, publicRoot);

  const response = await fetch(`${baseUrl}/healthz`);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
  assert.deepEqual(await response.json(), {
    service: 'SR.BSM',
    status: 'ok',
    surface: 'public',
  });
});

test('SR.BSM public server maps root to the trust center', async (t) => {
  const publicRoot = await mkdtemp(join(tmpdir(), 'sr-bsm-public-'));
  await import('node:fs/promises').then(({ mkdir }) => mkdir(join(publicRoot, 'trust'), { recursive: true }));
  await writeFile(join(publicRoot, 'trust', 'index.html'), '<h1>LexPrim Trust Center</h1>');
  const baseUrl = await withServer(t, publicRoot);

  const response = await fetch(`${baseUrl}/`);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('content-type'), 'text/html; charset=utf-8');
  assert.match(await response.text(), /LexPrim Trust Center/);
});

test('SR.BSM public server returns JSON 404 for missing public files', async (t) => {
  const publicRoot = await mkdtemp(join(tmpdir(), 'sr-bsm-public-'));
  const baseUrl = await withServer(t, publicRoot);

  const response = await fetch(`${baseUrl}/missing.html`);
  assert.equal(response.status, 404);
  assert.deepEqual(await response.json(), { status: 'not_found' });
});

test('SR.BSM public server blocks path traversal', async () => {
  const publicRoot = await mkdtemp(join(tmpdir(), 'sr-bsm-public-'));
  assert.equal(resolvePublicPath('/../package.json', publicRoot), null);
});

test('SR.BSM public server returns expected content types', () => {
  assert.equal(getContentType('index.html'), 'text/html; charset=utf-8');
  assert.equal(getContentType('app.js'), 'text/javascript; charset=utf-8');
  assert.equal(getContentType('unknown.bin'), 'application/octet-stream');
});
