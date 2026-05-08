# Execution Discipline Maximum Addendum

This addendum captures enforceable response semantics for agent execution reports.

## Allowed terminal statuses

Use only the following terminal statuses when reporting execution outcomes:

- `VERIFIED_FIXED`
- `PARTIALLY_APPLIED`
- `CHANGED_BUT_NOT_VERIFIED`
- `BLOCKED`
- `UNVERIFIED`
- `NOT_STARTED`
- `SUPERSEDED`
- `CONFLICTED`

## Mandatory report shape

Every execution report must include:

- `Execution Verdict`
- `Status`
- `Scope`
- `Canonical Path`
- `Files Touched`
- `Blockers`
- `Hot Surface Risk`
- `What Was Actually Changed`
- `What Was Actually Verified`
- `What Remains Unverified`
- `Next Valid Action`

When no direct validation reached the true failing path, `What Was Actually Verified` must be `none`.

## Blocker taxonomy

When execution is blocked, classify blockers with these codes:

- `AUTH_MISSING`
- `AUTH_INVALID`
- `AUTH_EXPIRED`
- `CONFIG_NOT_FOUND`
- `SYNTAX_FAILURE`
- `TYPE_FAILURE`
- `TEST_FAILURE`
- `RUNTIME_FAILURE`
- `WORKFLOW_CONFLICT`
- `HOT_SURFACE_CONFLICT`
- `SECRET_MISSING`
- `DEPLOYMENT_BLOCKED`
- `UNVERIFIED_RUNTIME`
