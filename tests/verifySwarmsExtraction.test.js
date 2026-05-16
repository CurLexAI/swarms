import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const scriptPath = path.join(process.cwd(), 'scripts/verify_swarms_extraction.sh');

test('verify_swarms_extraction.sh uses portable executable bash syntax', () => {
  const source = fs.readFileSync(scriptPath, 'utf8');

  assert.match(source, /^#!\/usr\/bin\/env bash/m);
  assert.match(source, /set -Eeuo pipefail/);

  assert.doesNotMatch(source, /[“”]/, 'smart quotes are forbidden');
  assert.doesNotMatch(source, /[–—]/, 'unicode dashes are forbidden');

  assert.match(source, /require_file "\.agents\/config\/agents\.yaml"/);
  assert.match(source, /legacy agents\/registry\.yaml is present/);

  assert.match(source, /find .* -prune -o -type f -name '\*\.zip'/s);
  assert.match(source, /PASS: swarms extraction structure is executable and canonical/);
});

test('verify_swarms_extraction.sh fails loudly when forbidden legacy registry exists', () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'swarms-negative-'));

  fs.mkdirSync(path.join(tmpRoot, '.agents', 'config'), { recursive: true });
  fs.mkdirSync(path.join(tmpRoot, 'agents'), { recursive: true });
  fs.mkdirSync(path.join(tmpRoot, 'scripts'), { recursive: true });
  fs.mkdirSync(path.join(tmpRoot, 'tests'), { recursive: true });
  fs.mkdirSync(path.join(tmpRoot, 'src', 'services'), { recursive: true });

  fs.writeFileSync(path.join(tmpRoot, 'AGENTS.md'), '# test');
  fs.writeFileSync(path.join(tmpRoot, 'README.md'), '# test');
  fs.writeFileSync(path.join(tmpRoot, 'package.json'), '{"name":"tmp"}');
  fs.writeFileSync(path.join(tmpRoot, '.agents/config/agents.yaml'), 'agents: {}');
  fs.writeFileSync(path.join(tmpRoot, 'src/services/unifiedAgentAdapter.ts'), 'export {};');

  fs.writeFileSync(
    path.join(tmpRoot, 'agents/registry.yaml'),
    'legacy: forbidden\n'
  );

  try {
    execFileSync('bash', [scriptPath, tmpRoot], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe']
    });

    assert.fail('script must fail when forbidden registry path exists');
  } catch (error) {
    const stderr = String(error.stderr ?? '');

    assert.match(
      stderr,
      /legacy agents\/registry\.yaml is present/i
    );
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});