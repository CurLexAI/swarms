# Agent Launch Evidence

Status: **UNVERIFIED** — this file is a template. It MUST be updated by the
release operator with concrete, link-backed evidence before any "ready"
claim is permitted.

The fields below are normative. An empty or `PENDING` field means the
corresponding claim is not yet supported by evidence. No PR labelled
`launch-ready` may merge while any P0 row is `PENDING`.

---

## 1. Provenance

| Field          | Value     |
|----------------|-----------|
| Recorded at    | PENDING   |
| Recorded by    | PENDING   |
| Commit SHA     | PENDING   |
| Branch         | PENDING   |
| Workflow run   | PENDING   |

## 2. Local Gates (P0)

Each row must reference an actual command run and its exit code.

| Gate                                                  | Result  | Evidence (path or run URL) |
|-------------------------------------------------------|---------|----------------------------|
| `scripts/commander/agent-presence-gate.sh`            | PENDING | PENDING                    |
| `scripts/commander/p0-security-test-gate.sh`          | PENDING | PENDING                    |
| `scripts/commander/modal-boundary-gate.sh`            | PENDING | PENDING                    |
| `.agents/skills/codex-commander/scripts/codex_commander_gate.sh` | PENDING | PENDING |

## 3. Test Suites (P0)

| Suite                                  | Pass / Total | Evidence |
|----------------------------------------|--------------|----------|
| `tests.test_bayyinah_validation_gate`  | PENDING      | PENDING  |
| `tests.test_router_policy`             | PENDING      | PENDING  |
| `tests.test_pr_review_modal_relay`     | PENDING      | PENDING  |
| Node integration tests (`tests/*.test.js`) | PENDING  | PENDING  |

## 4. Secrets Readiness

Presence only — values MUST NOT be recorded here. See
`docs/secrets-policy.md`.

| Secret              | Set in repo? | Set in env (CI run)? | Last rotated |
|---------------------|--------------|----------------------|--------------|
| `BAYYINAH_ENDPOINT` | PENDING      | PENDING              | PENDING      |
| `MIHWAR_ENDPOINT`   | PENDING      | PENDING              | PENDING      |
| `AGENT_API_TOKEN`   | PENDING      | PENDING              | PENDING      |

## 5. Runtime Smoke Tests

A smoke test counts only when invoked against the deployed Modal endpoint
from a CI run with the production secrets bound. Local invocations and
mocked relays do NOT satisfy this row.

| Agent      | Endpoint reachable | Verdict roundtrip | Evidence |
|------------|--------------------|-------------------|----------|
| Bayyinah   | PENDING            | PENDING           | PENDING  |
| Mihwar     | PENDING            | PENDING           | PENDING  |

## 6. Edge / Deploy Readiness

Deploy claims are blocked until the corresponding row is filled with a
deploy URL **and** a successful health-check response from that URL.

| Surface       | Deployed URL | Health check | Evidence |
|---------------|--------------|--------------|----------|
| Render API    | PENDING      | PENDING      | PENDING  |
| Cloudflare    | PENDING      | PENDING      | PENDING  |

## 7. Outstanding Blockers

List every blocker the latest COMMANDER REPORT raised, with the PR or
commit that resolves it. Do not delete rows; mark them `RESOLVED`.

| ID                | Description | Resolved by |
|-------------------|-------------|-------------|
| AUTH_MISSING      | PENDING     | PENDING     |
| CONFIG_NOT_FOUND  | PENDING     | PENDING     |
| SECRET_MISSING    | PENDING     | PENDING     |
| TEST_FAILURE      | PENDING     | PENDING     |

## 8. Sign-off

Sign-off is only valid if every P0 row above is filled with non-`PENDING`
evidence and the latest COMMANDER REPORT verdict is `READY`.

- Operator: PENDING
- Date: PENDING
- COMMANDER REPORT verdict: PENDING
