import { readFileSync } from 'node:fs';

const REQUIRED_SNIPPETS = [
  "name: SR.BSM",
  "runtime: node",
  "healthCheckPath: /healthz",
  "autoDeploy: false",
  "name: Strict-Transport-Security",
  "value: max-age=63072000; includeSubDomains; preload",
  "name: X-Frame-Options",
  "value: DENY",
  "name: X-Content-Type-Options",
  "value: nosniff",
  "name: Referrer-Policy",
  "value: strict-origin-when-cross-origin",
  "name: Permissions-Policy",
  "value: camera=(), microphone=(), geolocation=(), payment=()",
  "name: Cross-Origin-Embedder-Policy",
  "value: require-corp",
  "name: Cross-Origin-Opener-Policy",
  "value: same-origin",
  "name: Cross-Origin-Resource-Policy",
  "value: same-origin",
  "name: Content-Security-Policy",
  "value: default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; frame-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'",
];

function fail(message) {
  console.error(`render.yaml validation failed: ${message}`);
  process.exit(1);
}

const renderConfig = readFileSync(new URL('../render.yaml', import.meta.url), 'utf8');

if ((renderConfig.match(/^\s*- type:\s+web$/gm) ?? []).length !== 1) {
  fail('expected exactly one web service in render.yaml');
}

for (const snippet of REQUIRED_SNIPPETS) {
  if (!renderConfig.includes(snippet)) {
    fail(`missing required snippet: ${snippet}`);
  }
}

if (renderConfig.includes('cdn.example.com')) {
  fail('content-security-policy must not allow cdn.example.com for the static trust surface');
}

console.log('render.yaml validation passed');
