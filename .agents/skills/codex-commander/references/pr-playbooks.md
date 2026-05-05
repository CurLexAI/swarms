# PR Playbooks

## P0 Bayyinah + Router Policy Tests

Branch: `test/p0-bayyinah-router-policy`

Title: `test: add P0 Bayyinah validation and router policy coverage`

Files:

- `tests/test_bayyinah_validation_gate.py`
- `tests/test_router_policy.py`
- `scripts/commander/p0-security-test-gate.sh`
- `docs/operations/p0-security-test-plan.md`

Acceptance criteria:

- Tests cover `BLOCK` vs `BLOCKED` verdict contract.
- Tests expose false positives on citation URLs such as `https://` if still present.
- Tests cover Arabic and English prompt-injection phrases.
- Tests prove CRITICAL findings dominate final verdict.
- Tests prove legal/regulatory outputs without citations are blocked or request changes.

## Registry Fallback Fix

Branch: `fix/agent-registry-fallback`

Title: `Add fallback agent registry path for UnifiedAgentAdapter`

Files:

- `src/services/unifiedAgentAdapter.ts`
- Relevant adapter registry tests.

Acceptance criteria:

- Primary and fallback registry paths are explicit.
- Missing both registries fails closed with `CONFIG_NOT_FOUND`.
- PR description says this is infrastructure only and does not launch agents.

## Optional Import Skip Policy

Branch: `fix/test-optional-import-skip-policy`

Title: `Fail closed on non-optional import failures in agent adapter tests`

Acceptance criteria:

- Skip only `ERR_MODULE_NOT_FOUND`, `MODULE_NOT_FOUND`, or missing package `typescript`.
- Re-throw syntax errors, runtime errors, and broken internal imports.

## Verified Agent Launch Gate

Branch: `feat/verified-agent-launch-gate`

Title: `Add verified agent launch gate and evidence artifact`

Acceptance criteria:

- Emits `READY`, `PARTIAL`, or `BLOCKED`.
- Missing Bayyinah secrets becomes `SKIPPED_UNVERIFIED`.
- Release-candidate PR fails unless review is verified.

## Modal Agent Smoke Tests

Branch: `feat/modal-agent-smoke-tests`

Title: `Add Modal smoke tests for Bayyinah and Mihwar endpoints`

Acceptance criteria:

- Does not print private endpoints or tokens.
- Missing secrets warn for non-release PRs and fail for release PRs.
- Endpoint failure fails the check.

## Copilot-to-Modal Gateway

Branch: `feat/copilot-modal-gateway`

Title: `Route private Copilot agents through Render gateway to Modal`

Acceptance criteria:

- Does not claim GitHub Copilot model picker replacement.
- Public clients call Render, not Modal.
- Gateway calls Modal server-side only.
- Smoke test proves gateway path works.
