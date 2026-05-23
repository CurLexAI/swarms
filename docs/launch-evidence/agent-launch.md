# Agent Launch Evidence

Status: **PARTIAL** — Local P0 gates and test suites verified. Runtime
smoke tests and edge deploy readiness remain UNVERIFIED (require secrets
and deployed infrastructure).

The fields below are normative. An empty or `PENDING` field means the
corresponding claim is not yet supported by evidence. No PR labelled
`launch-ready` may merge while any P0 row is `PENDING`.

---

## 1. Provenance

| Field          | Value     |
|----------------|-----------|
| Recorded at    | 2026-05-23T02:07Z |
| Recorded by    | Cloud Agent (automated) |
| Commit SHA     | 57017b3aed0bc6892c77ea83c0ee4b6bc8b733cc |
| Branch         | main |
| Workflow run   | SKIPPED_UNVERIFIED — local execution only |

## 2. Local Gates (P0)

Each row must reference an actual command run and its exit code.

| Gate                                                  | Result  | Evidence (path or run URL) |
|-------------------------------------------------------|---------|----------------------------|
| `scripts/commander/agent-presence-gate.sh`            | PASS    | exit 0; configured_agent_count=3 (mihwar, bayyinah, copilot_swe) |
| `scripts/commander/p0-security-test-gate.sh`          | PASS    | exit 0; "Ran 52 tests in 0.027s — OK" |
| `scripts/commander/modal-boundary-gate.sh`            | PASS    | exit 0; no *.modal.run in src,public; no Modal SDK in client; SECRET_MISSING warnings expected outside CI |
| `.agents/skills/codex-commander/scripts/codex_commander_gate.sh` | PASS | exit 0; AGENTS.md present; agents.yaml present; no direct Modal URL |

## 3. Test Suites (P0)

| Suite                                  | Pass / Total | Evidence |
|----------------------------------------|--------------|----------|
| `tests.test_bayyinah_validation_gate`  | 24 / 24      | pytest exit 0 |
| `tests.test_router_policy`             | 28 / 28      | pytest exit 0 |
| `tests.test_pr_review_modal_relay`     | 7 / 7        | pytest exit 0 |
| Node integration tests (`tests/*.test.js`) | 98 / 98  | node --test exit 0 |

## 4. Secrets Readiness

Presence only — values MUST NOT be recorded here. See
`docs/secrets-policy.md`.

| Secret              | Set in repo? | Set in env (CI run)? | Last rotated |
|---------------------|--------------|----------------------|--------------|
| `BAYYINAH_ENDPOINT` | UNSET        | UNVERIFIED           | UNVERIFIED   |
| `MIHWAR_ENDPOINT`   | UNSET        | UNVERIFIED           | UNVERIFIED   |
| `AGENT_API_TOKEN`   | UNSET        | UNVERIFIED           | UNVERIFIED   |

## 5. Runtime Smoke Tests

A smoke test counts only when invoked against the deployed Modal endpoint
from a CI run with the production secrets bound. Local invocations and
mocked relays do NOT satisfy this row.

| Agent      | Endpoint reachable | Verdict roundtrip | Evidence |
|------------|--------------------|-------------------|----------|
| Bayyinah   | SKIPPED_UNVERIFIED | SKIPPED_UNVERIFIED | Secrets not available in this environment |
| Mihwar     | SKIPPED_UNVERIFIED | SKIPPED_UNVERIFIED | Secrets not available in this environment |

## 6. Edge / Deploy Readiness

Deploy claims are blocked until the corresponding row is filled with a
deploy URL **and** a successful health-check response from that URL.

| Surface       | Deployed URL | Health check | Evidence |
|---------------|--------------|--------------|----------|
| Render API    | SKIPPED_UNVERIFIED | SKIPPED_UNVERIFIED | No deploy credentials available |
| Cloudflare    | SKIPPED_UNVERIFIED | SKIPPED_UNVERIFIED | No deploy credentials available |

## 7. Outstanding Blockers

List every blocker the latest COMMANDER REPORT raised, with the PR or
commit that resolves it. Do not delete rows; mark them `RESOLVED`.

| ID                | Description | Resolved by |
|-------------------|-------------|-------------|
| AUTH_MISSING      | NOT_APPLICABLE — no auth-gated local path failed | N/A |
| CONFIG_NOT_FOUND  | NOT_APPLICABLE — loadRegistry resolves .agents/config/agents.yaml successfully | N/A |
| SECRET_MISSING    | BAYYINAH_ENDPOINT, MIHWAR_ENDPOINT, AGENT_API_TOKEN not set; expected outside CI/runtime | Awaiting secrets configuration in deployment environment |
| TEST_FAILURE      | RESOLVED — all 171 Python + 98 Node tests pass at HEAD 57017b3 | This commit |

## 8. Sign-off

Sign-off is only valid if every P0 row above is filled with non-`PENDING`
evidence and the latest COMMANDER REPORT verdict is `READY`.

- Operator: PENDING (requires human approval after runtime verification)
- Date: PENDING
- COMMANDER REPORT verdict: LOCAL_READY — all local P0 gates pass; runtime verification blocked on secrets
