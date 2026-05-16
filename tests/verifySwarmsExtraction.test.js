import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

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
