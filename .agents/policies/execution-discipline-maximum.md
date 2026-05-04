# Execution Discipline Maximum Policy

This policy defines mandatory execution behavior for repository agents and contributors operating in high-discipline mode.

## Allowed Final Status Values

Use only:

- VERIFIED_FIXED
- PARTIALLY_APPLIED
- CHANGED_BUT_NOT_VERIFIED
- BLOCKED
- UNVERIFIED
- NOT_STARTED
- SUPERSEDED
- CONFLICTED

## Mandatory Execution Sequence

1. Establish runtime truth.
2. Establish canonical path.
3. Detect blockers.
4. Detect hot-surface conflicts.
5. Build plan of record.
6. Apply minimal correct change.
7. Verify actual impact on the real failure path.
8. Report status.

## Blocker Taxonomy

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

## Claim Discipline

Do not claim that work is fixed unless verification was executed on the real affected path.

If changes were made without end-to-end verification, use `CHANGED_BUT_NOT_VERIFIED`.

## Required Report Shape

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
