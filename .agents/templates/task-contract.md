# Task Contract

## Objective
Execute one measurable change only.

## Repository
CurLexAI/swarms

## Scope
Allowed files:
- <file-path-1>
- <file-path-2>

Forbidden:
- no secrets exposure
- no external AI API calls without explicit authorization
- no provider/runtime/deploy edits unless explicitly requested
- no unrelated refactors
- no broad formatting-only churn

## Expected Change
Describe the exact observable change.

## Verification
Run only relevant checks for the changed surface.

Example baseline:
```bash
python .agents/validate.py
python -m py_compile .agents/*.py
```

## Evidence
Report:
- files touched
- commands run
- outputs summary
- remaining unverified items
- final status (VERIFIED_FIXED | PARTIALLY_APPLIED | CHANGED_BUT_NOT_VERIFIED | BLOCKED | UNVERIFIED | NOT_STARTED | SUPERSEDED | CONFLICTED)

