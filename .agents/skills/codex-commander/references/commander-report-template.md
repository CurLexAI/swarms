# Commander Report Template

Use this template at the end of any Codex Commander run.

```text
=== COMMANDER REPORT ===
Mission:
Repository:
Branch:
Priority:
Owner:
Status: PASS | PARTIAL_PASS | FAIL | BLOCKED | UNVERIFIED

VERIFIED:
- 

INFERRED:
- 

UNVERIFIED:
- 

CHANGED:
- 

VALIDATION:
- command: 
  result: PASS | FAIL | SKIPPED | NOT_APPLICABLE | UNVERIFIED
  evidence: 

RISKS:
- CRITICAL:
- HIGH:
- MEDIUM:
- LOW:

DECISION: GO | NO-GO | REQUEST_CHANGES | MERGE_ALLOWED | MERGE_BLOCKED
NEXT ACTION:
```

Rules:

- Never report runtime activation as `VERIFIED` without a smoke test.
- Never collapse skipped checks into pass.
- If secrets are missing, report `SKIPPED_UNVERIFIED`, not success.
- If a command is not applicable because a file is absent, say `NOT_APPLICABLE` and cite the missing file.
