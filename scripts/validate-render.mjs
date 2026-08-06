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
const REQUIRED_HEADER_PATH = '/*';
const LOCKED_DOWN_NONE_DIRECTIVES = ['script-src', 'connect-src', 'object-src', 'frame-src'];

function fail(message) {
  console.error(`render.yaml validation failed: ${message}`);
  process.exit(1);
}

function parseCsp(csp) {
  const directives = new Map();

  for (const segment of csp.split(';')) {
    const trimmed = segment.trim();
    if (!trimmed) continue;

    const parts = trimmed.split(/\s+/);
    const [name, ...values] = parts;
    directives.set(name, values);
  }

  return directives;
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

for (const [name, value] of REQUIRED_HEADERS) {
  const header = headerEntries.find((entry) => entry?.name === name);
  if (!header) {
    fail(`missing header ${name}`);
  }

  if (header.path !== REQUIRED_HEADER_PATH) {
    fail(`header ${name} must apply to ${REQUIRED_HEADER_PATH}, found ${header.path ?? 'undefined'}`);
  }

  if (header.value !== value) {
    fail(`missing or mismatched header ${name}`);
  }
}

const csp = headerEntries.find((entry) => entry?.name === 'Content-Security-Policy')?.value;
const cspDirectives = parseCsp(csp ?? '');

for (const directive of LOCKED_DOWN_NONE_DIRECTIVES) {
  const values = cspDirectives.get(directive);
  if (!values) {
    fail(`content-security-policy missing ${directive}`);
  }

  if (values.length !== 1 || values[0] !== "'none'") {
    fail(`content-security-policy ${directive} must be exactly 'none'`);
  }
}

if (csp.includes('cdn.example.com')) {
  fail('content-security-policy must not allow cdn.example.com for the static trust surface');
}

console.log('render.yaml validation passed');
