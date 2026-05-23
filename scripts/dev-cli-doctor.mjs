#!/usr/bin/env node
import { spawnSync } from 'node:child_process';

const checks = [
  { name: 'git status', cmd: 'git', args: ['status', '--short', '--branch'] },
  { name: 'codex --version', cmd: 'codex', args: ['--version'] },
  { name: 'gemini --version', cmd: 'gemini', args: ['--version'] },
  { name: 'ollama list', cmd: 'ollama', args: ['list'] },
  { name: 'gh auth status', cmd: 'gh', args: ['auth', 'status'] }
];

let missing = 0;
for (const check of checks) {
  const res = spawnSync(check.cmd, check.args, { encoding: 'utf8' });
  if (res.error && res.error.code === 'ENOENT') {
    missing += 1;
    console.log(`MISSING_TOOL ${check.cmd}`);
    continue;
  }
  if (res.status !== 0) {
    console.log(`FAIL ${check.name}`);
    if (res.stdout) process.stdout.write(res.stdout);
    if (res.stderr) process.stderr.write(res.stderr);
    continue;
  }
  console.log(`OK ${check.name}`);
  if (res.stdout) process.stdout.write(res.stdout);
}

if (missing > 0) {
  process.exitCode = 2;
}
