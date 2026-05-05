# P0 Security Test Plan — Bayyinah Validation Gate + Router Policy

## Scope

This P0 gate validates security-critical and policy-critical contracts for:

- `.agents/validators/bayyinah_validation_gate.py`
- `.agents/router/task_classifier.py`
- `.agents/router/model_policy_engine.py`
- `.agents/router/model_router.py`

## Test Files

- `tests/test_bayyinah_validation_gate.py`
- `tests/test_router_policy.py`

## Why this gate exists

These tests are intentionally behavioral and contract-focused. They are designed to fail when production behavior drifts from policy expectations.

## Contracts covered

### CRITICAL

- Validation verdict contract must emit `BLOCKED` (not `BLOCK`) for blocking outcomes.
- Critical findings dominate final verdict and severity.

### HIGH

- Citation URLs (`https://...`) must not be treated as unauthorized network execution.
- Legal/regulatory responses requiring citations must enforce citation discipline.
- Prompt-injection indicators in English/Arabic are detected by policy path.
- Blocking severity ordering is preserved.

### MEDIUM

- Classifier whole-word matching avoids substring false positives (e.g., `decode` should not map to coding via `code`).
- Arabic legal prompts classify to `legal_analysis` with high-risk handling.
- High-risk/legal routes require Bayyinah reviewer where policy requires it.
- Execution plans include Bayyinah validation step when risk requires validation.

## Execution

```bash
bash scripts/commander/p0-security-test-gate.sh .
```

## Interpretation

- Failing tests indicate production defects or policy drift.
- Do not weaken tests to force green.
- Fix production behavior and re-run gate.
