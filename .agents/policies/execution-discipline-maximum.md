# Execution Discipline Maximum Policy

This policy defines mandatory execution behavior for repository agents and contributors operating in high-discipline mode.

## 1) Claim Integrity

- Do not claim outcomes without direct evidence from commands, runtime behavior, or repository artifacts.
- Do not treat file edits, commits, or PR creation as proof of runtime correctness.
- If verification is missing on the real failure path, report `CHANGED_BUT_NOT_VERIFIED`.
- If a blocker prevents verification, report `BLOCKED` and classify it.

## 2) Allowed Final Status Values

Use only:

- VERIFIED_FIXED
- PARTIALLY_APPLIED
- CHANGED_BUT_NOT_VERIFIED
- BLOCKED
- UNVERIFIED
- NOT_STARTED
- SUPERSEDED
- CONFLICTED

## 3) Mandatory Execution Sequence

1. Establish runtime truth.
2. Establish canonical path.
3. Detect blockers.
4. Detect hot-surface conflicts.
5. Build plan of record.
6. Apply minimal correct change.
7. Verify actual impact on the real failure path.
8. Report status.

## 4) Blocker Taxonomy

When blocked, classify blockers using one of:

- AUTH_MISSING
- AUTH_INVALID
- AUTH_EXPIRED
- CONFIG_NOT_FOUND
- SYNTAX_FAILURE
- TYPE_FAILURE
- TEST_FAILURE
- RUNTIME_FAILURE
- WORKFLOW_CONFLICT
- HOT_SURFACE_CONFLICT
- SECRET_MISSING
- DEPLOYMENT_BLOCKED
- UNVERIFIED_RUNTIME

Do not repeat the same failing action after a blocker is confirmed.

## 5) Hot Surface Discipline

- Treat shared adapters, workflows, deploy paths, auth paths, and contract files as hot surfaces.
- Do not open parallel implementation tracks on the same hot surface.
- Re-check base branch and active changes before starting or reopening work on a hot surface.

## 6) Verification Discipline

- Verify on the same layer as the failure type (runtime/workflow/adapter/auth/deploy/endpoint).
- A passing unrelated check does not prove system correctness.
- If tests do not reach the affected execution path, verification is insufficient.

## 7) Required Report Shape

Use this structure for execution reports:

```text
Execution Verdict:
- Status:
- Scope:
- Canonical Path:
- Files Touched:
- Blockers:
- Hot Surface Risk:
- What Was Actually Changed:
- What Was Actually Verified:
- What Remains Unverified:
- Next Valid Action:
```
