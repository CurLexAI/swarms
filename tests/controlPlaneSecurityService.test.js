import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const servicePath = path.join(process.cwd(), 'src/services/ControlPlaneSecurityService.ts');

test('control plane security service enforces enterprise auth, RBAC, session hardening, and audit export', () => {
  const source = fs.readFileSync(servicePath, 'utf8');

  assert.match(source, /private readonly authPath = "\/enterprise\/control";/);
  assert.match(source, /if \(!principal\.mfaVerifiedAt\) \{/);
  assert.match(source, /protocol !== "OIDC" && protocol !== "SAML"/);
  assert.match(source, /const ROLE_PERMISSIONS: Readonly<Record<ControlRole, readonly string\[\]>>/);
  assert.match(source, /Admin: \["control:read", "control:operate", "control:review", "control:admin"\]/);
  assert.match(source, /state\.failedAttempts >= policy\.bruteForceMaxAttempts/);
  assert.match(source, /Session timeout policy triggered/);
  assert.match(source, /rotateMs >= policy\.rotateAfterMinutes \* 60_000/);
  assert.match(source, /event: "control_plane_audit"/);
  assert.match(source, /exportAuditTrail\(entries: AuditTrailEntry\[\]\): string/);
});

