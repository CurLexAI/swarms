---
name: repo-production-auditor
description: audit repository production readiness for agent operations, ci/cd, secrets, dependency posture, github actions, docker boundaries, modal backend-only rules, and deployment evidence. use when asked whether the repository is ready for production, what remains, or to verify all work from start to finish.
---

# Repository Production Auditor

## Scope

Audit `CurLexAI/swarms` as an agent operations repository, not as the LexPrim/Qarar app monorepo.

## Required checks

```bash
git status --short
git branch --show-current
python3 -m py_compile .agents/*.py
python3 .agents/validate.py
python3 .agents/invoke.py info
python3 -m pytest -q tests/
npm test
npx tsc --noEmit
npm run check

bash scripts/commander/p0-security-test-gate.sh .
bash scripts/commander/modal-boundary-gate.sh .
bash scripts/commander/adr-0001-boundary-gate.sh .
bash scripts/commander/agent-presence-gate.sh .
bash .agents/skills/codex-commander/scripts/codex_commander_gate.sh .
```

## Evidence labels

* VERIFIED
* INFERRED
* UNVERIFIED
* SKIPPED_UNVERIFIED
* NOT_APPLICABLE

## Readiness rule

Never mark production READY if:

* smoke tests are absent,
* runtime secrets are unset,
* CRITICAL/HIGH findings exist,
* boundary gates fail,
* TypeScript blocker is unresolved unless documented as accepted risk.
