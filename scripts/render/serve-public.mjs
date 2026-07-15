import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer as createHttpServer } from 'node:http';
import { extname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const DEFAULT_PUBLIC_ROOT = resolve(REPO_ROOT, 'public');
const DEFAULT_PORT = 10000;

const CONTENT_TYPES = new Map([
  ['.css', 'text/css; charset=utf-8'],
  ['.html', 'text/html; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.map', 'application/json; charset=utf-8'],
  ['.svg', 'image/svg+xml'],
  ['.txt', 'text/plain; charset=utf-8'],
  ['.webmanifest', 'application/manifest+json; charset=utf-8'],
]);

const SECURITY_HEADERS = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self' https://cdn.example.com; style-src 'unsafe-inline' 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'",
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
};

function isInside(basePath, candidatePath) {
  const normalizedBase = resolve(basePath);
  const normalizedCandidate = resolve(candidatePath);
  return normalizedCandidate === normalizedBase || normalizedCandidate.startsWith(`${normalizedBase}${sep}`);
}

export function getContentType(filePath) {
  return CONTENT_TYPES.get(extname(filePath).toLowerCase()) ?? 'application/octet-stream';
}

export function resolvePublicPath(requestPath, publicRoot = DEFAULT_PUBLIC_ROOT) {
  const normalizedPublicRoot = resolve(publicRoot);
  const decodedPath = decodeURIComponent(requestPath.split('?')[0] || '/');
  const routePath = decodedPath === '/' ? '/trust/index.html' : decodedPath;
  const candidatePath = resolve(join(normalizedPublicRoot, routePath));

  if (!isInside(normalizedPublicRoot, candidatePath)) {
    return null;
  }

  return candidatePath;
}

function writeSecurityHeaders(response, extraHeaders = {}) {
  for (const [key, value] of Object.entries({ ...SECURITY_HEADERS, ...extraHeaders })) {
    response.setHeader(key, value);
  }
}

function writeJson(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  writeSecurityHeaders(response, {
    'Cache-Control': 'no-store',
    'Content-Length': Buffer.byteLength(body),
    'Content-Type': 'application/json; charset=utf-8',
  });
  response.writeHead(statusCode);
  response.end(body);
}

async function streamFile(response, filePath) {
  let fileStat;
  try {
    fileStat = await stat(filePath);
  } catch {
    writeJson(response, 404, { status: 'not_found' });
    return;
  }

  if (!fileStat.isFile()) {
    writeJson(response, 404, { status: 'not_found' });
    return;
  }

  writeSecurityHeaders(response, {
    'Cache-Control': 'public, max-age=300',
    'Content-Length': fileStat.size,
    'Content-Type': getContentType(filePath),
  });
  response.writeHead(200);
  createReadStream(filePath).pipe(response);
}

export function createPublicServer({ publicRoot = DEFAULT_PUBLIC_ROOT } = {}) {
  return createHttpServer(async (request, response) => {
    const requestUrl = new URL(request.url ?? '/', 'http://localhost');

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      writeJson(response, 405, { status: 'method_not_allowed' });
      return;
    }

    if (requestUrl.pathname === '/healthz') {
      writeJson(response, 200, {
        service: 'SR.BSM',
        status: 'ok',
        surface: 'public',
      });
      return;
    }

    const resolvedPath = resolvePublicPath(requestUrl.pathname, publicRoot);
    if (resolvedPath === null) {
      writeJson(response, 404, { status: 'not_found' });
      return;
    }

    await streamFile(response, resolvedPath);
  });
}

export function startServer({ port = Number.parseInt(process.env.PORT ?? `${DEFAULT_PORT}`, 10), publicRoot = DEFAULT_PUBLIC_ROOT } = {}) {
  const server = createPublicServer({ publicRoot });
  server.listen(port, '0.0.0.0', () => {
    console.log(`SR.BSM public service listening on port ${port}`);
  });
  return server;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  startServer();
}
