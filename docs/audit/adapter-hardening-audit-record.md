# Adapter Hardening Audit Record

Status: PATCHED_NOT_EXECUTED
Branch: fix/adapter-registry-and-extraction-gates

## Scope

Additive hardening only.

No replacement of:
- PolicyService
- capability enforcement
- backend allowlist validation
- runtime verification
- blocker classification
- audit sanitization

## Files Added

- scripts/verify_swarms_extraction.sh
- tests/verifySwarmsExtraction.test.js

## Files Updated

- package.json

## Canonical Registry Authority

Canonical registry path remains:

.agents/config/agents.yaml

Legacy path explicitly rejected:

agents/registry.yaml

## Governance Intent

Prevent split-brain registry loading between:
- extraction validators
- runtime adapter
- future CI checks

## Required Verification Before Merge

1. Execute bash scripts/verify_swarms_extraction.sh .
2. Execute npm run test:extraction
3. Execute negative fault injection with agents/registry.yaml present
4. Verify non-zero exit code and explicit failure message
5. Run full npm run check

## Risk Classification

Hot surface: HIGH
Blast radius: unifiedAgentAdapter.ts + repository validation path

## Merge Rule

Do not merge while status remains PATCHED_NOT_EXECUTED.
