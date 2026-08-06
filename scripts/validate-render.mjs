import { readFileSync } from 'node:fs';
import { load } from 'js-yaml';

const REQUIRED_HEADERS = new Map([
  ['Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload'],
  ['X-Frame-Options', 'DENY'],
  ['X-Content-Type-Options', 'nosniff'],
  ['Referrer-Policy', 'strict-origin-when-cross-origin'],
  ['Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=()'],
  ['Cross-Origin-Embedder-Policy', 'require-corp'],
  ['Cross-Origin-Opener-Policy', 'same-origin'],
  ['Cross-Origin-Resource-Policy', 'same-origin'],
]);

function fail(message) {
  console.error(`render.yaml validation failed: ${message}`);
  process.exit(1);
}

const renderConfig = load(readFileSync(new URL('../render.yaml', import.meta.url), 'utf8'));
const services = Array.isArray(renderConfig?.services) ? renderConfig.services : [];

if (services.length !== 1) {
  fail(`expected exactly one service, found ${services.length}`);
}

const [service] = services;

if (service.name !== 'SR.BSM') {
  fail(`expected service name SR.BSM, found ${service.name ?? 'undefined'}`);
}

if (service.runtime !== 'node') {
  fail(`expected runtime node, found ${service.runtime ?? 'undefined'}`);
}

if (service.healthCheckPath !== '/healthz') {
  fail(`expected healthCheckPath /healthz, found ${service.healthCheckPath ?? 'undefined'}`);
}

if (service.autoDeploy !== false) {
  fail(`expected autoDeploy false, found ${service.autoDeploy}`);
}

const headerEntries = Array.isArray(service.headers) ? service.headers : [];
const headerMap = new Map(headerEntries.map((header) => [header.name, header.value]));

for (const [name, value] of REQUIRED_HEADERS) {
  if (headerMap.get(name) !== value) {
    fail(`missing or mismatched header ${name}`);
  }
}

const csp = headerMap.get('Content-Security-Policy');
if (!csp) {
  fail('missing Content-Security-Policy header');
}

for (const directive of ["script-src 'none'", "connect-src 'none'", "object-src 'none'", "frame-src 'none'"]) {
  if (!csp.includes(directive)) {
    fail(`content-security-policy missing ${directive}`);
  }
}

if (csp.includes('cdn.example.com')) {
  fail('content-security-policy must not allow cdn.example.com for the static trust surface');
}

console.log('render.yaml validation passed');
