---
name: agent-runtime-auditor
description: audit private agent runtime for mihwar, bayyinah, qarar router, copilot swe, modal endpoints, model routing, validation gates, and smoke-test evidence. use when verifying private models, agent activation, model endpoints, route policy, or whether custom agents are ready to use.
---

# Agent Runtime Auditor

## Source of truth

Inspect:

- `.agents/config/agents.yaml`
- `.agents/modal_app.py`
- `.agents/invoke.py`
- `.agents/router/`
- `.agents/validators/bayyinah_validation_gate.py`
- `.github/workflows/agent-review.yml`
- `src/services/unifiedAgentAdapter.ts`

## Runtime rule

Do not claim active runtime until:
1. secrets are set,
2. Modal deploy succeeded,
3. smoke tests passed,
4. Bayyinah validation gate confirms no unresolved CRITICAL/HIGH.

## Model roles

- Mihwar: implementation/generation
- Bayyinah: review/validation
- Qarar Router: policy routing and risk classification
- Copilot SWE: scaffold-only executor

## Output

Return:

- VERIFIED
- UNVERIFIED
- BLOCKERS
- AGENTS TABLE
- MODEL ROUTING TABLE
- NEXT ACTION
