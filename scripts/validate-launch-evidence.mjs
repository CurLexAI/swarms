#!/usr/bin/env node
import { readFileSync } from 'node:fs';

const evidence = JSON.parse(readFileSync('docs/launch-evidence/launch-evidence.json', 'utf8'));
const allowedVerdicts = new Set(['READY', 'HOLD', 'REJECT']);
const requiredPhaseNames = [
  'Governance',
  'Secrets',
  'Local gates',
  'Modal deploy',
  'Modal CLI smoke',
  'Endpoint smoke',
  'Bayyinah PR gate',
  'Control boundary',
  'Device/connectivity pilot',
  'Limited live',
  'Full live',
];
const requiredSecretNames = [
  'MODAL_TOKEN_ID',
  'MODAL_TOKEN_SECRET',
  'HF_TOKEN',
  'MIHWAR_MODEL_REVISION',
  'BAYYINAH_MODEL_REVISION',
  'BAYYINAH_ENDPOINT',
  'MIHWAR_ENDPOINT',
  'BAYYINAH_API_TOKEN',
  'MIHWAR_API_TOKEN',
  'GITHUB_TOKEN',
  'MIHWAR_HMAC_SECRET',
  'QARAR_RAG_HMAC_SECRET',
  'MCP_BEARER_TOKEN',
  'SMOKE_TEST_TOKEN',
];

function fail(message) {
  console.error(`LAUNCH_EVIDENCE: FAIL - ${message}`);
  process.exit(1);
}

if (!allowedVerdicts.has(evidence.final_verdict)) {
  fail('final_verdict must be READY, HOLD, or REJECT');
}

if (evidence.final_verdict === 'READY') {
  const unresolved = evidence.phases?.flatMap((phase) => phase.blockers ?? []) ?? [];
  if (unresolved.length > 0) {
    fail('READY verdict is forbidden while phase blockers remain');
  }
}

if (evidence.no_auto_deploy_rule !== true) {
  fail('no_auto_deploy_rule must be true');
}

if (!Array.isArray(evidence.phases)) {
  fail('phases must be an array');
}

const phases = evidence.phases;
if (phases.length !== requiredPhaseNames.length) {
  fail(`expected ${requiredPhaseNames.length} phases`);
}

for (const [index, expectedName] of requiredPhaseNames.entries()) {
  const phase = phases[index];
  if (phase.order !== index + 1 || phase.name !== expectedName) {
    fail(`phase ${index + 1} must be ${expectedName}`);
  }
  if (!phase.status) {
    fail(`phase ${expectedName} must include status`);
  }
}

const secretNames = new Set(evidence.required_secret_names ?? []);
for (const name of requiredSecretNames) {
  if (!secretNames.has(name)) {
    fail(`missing required secret name ${name}`);
  }
}

const blockers = evidence.blockers_by_severity ?? {};
for (const severity of ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']) {
  if (!Array.isArray(blockers[severity])) {
    fail(`blockers_by_severity.${severity} must be an array`);
  }
}

console.log('LAUNCH_EVIDENCE: PASS');
console.log(`VERDICT: ${evidence.final_verdict}`);
console.log(`PHASES: ${phases.length}`);
console.log(`SECRET_NAMES: ${secretNames.size}`);
