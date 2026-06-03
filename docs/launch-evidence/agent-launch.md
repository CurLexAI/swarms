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
| `scripts/commander/agent-presence-gate.sh`            | PASS    | exit 0; configured_agent_count=2 (mihwar, bayyinah) — Copilot custom agents removed |
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
`docs/secrets-policy.md §1` for canonical scope and `§3` for the
operator runbook. Canonical scope is **Organization (LexPrime) →
Selected repositories: `CurLexAI/swarms`, `LexPrim/Qarar`**.

| Secret              | Set at canonical scope? | Visible to swarms runner? | Last rotated |
|---------------------|-------------------------|---------------------------|--------------|
| `BAYYINAH_ENDPOINT` | UNVERIFIED              | UNVERIFIED                | UNVERIFIED   |
| `MIHWAR_ENDPOINT`   | UNVERIFIED              | UNVERIFIED                | UNVERIFIED   |
| `BAYYINAH_API_TOKEN` | UNVERIFIED           | UNVERIFIED                | UNVERIFIED   |
| `MIHWAR_API_TOKEN`   | UNVERIFIED             | UNVERIFIED                | UNVERIFIED   |

Diagnostic shortcut: an `agent-review.yml` `bayyinah-review` job that
completes in < 30 s with conclusion `success` proves the secret is
**not visible to the runner** (workflow guard at lines 76–85 took the
`SKIPPED_UNVERIFIED` path). Either the secret is unset at canonical
scope, or `CurLexAI/swarms` was removed from the Selected repositories
allow-list. See `docs/secrets-policy.md §3.1` for the silent-degrade
warning.

## 5. Runtime Smoke Tests

A smoke test counts only when invoked against the deployed Modal endpoint
from a CI run with the production secrets bound. Local invocations and
mocked relays do NOT satisfy this row.

### How to run

The canonical smoke runner is `.github/workflows/modal-runtime-activation.yml` with `workflow_dispatch` and endpoint smoke enabled. The workflow contains `deploy_modal` and `run_smoke` inputs, and its endpoint smoke step uses service-specific bearer tokens for each endpoint. Operators may also run `scripts/commander/modal-runtime-smoke.sh` from a trusted backend shell after binding the same endpoint-specific secrets. The smoke path refuses to make any network call until all endpoint and token secrets are bound, never prints token or endpoint values, and never persists response bodies. Sample trusted-shell invocation:

```bash
BAYYINAH_ENDPOINT="$BAYYINAH_ENDPOINT" \
MIHWAR_ENDPOINT="$MIHWAR_ENDPOINT" \
BAYYINAH_API_TOKEN="$BAYYINAH_API_TOKEN" \
MIHWAR_API_TOKEN="$MIHWAR_API_TOKEN" \
bash scripts/commander/modal-runtime-smoke.sh
```

Exit codes:

| Exit | Meaning |
|------|---------|
| `0`  | `READY` — both endpoints answered 2xx with JSON-shaped bodies and rejected cross-token auth |
| `2`  | `HOLD` — one or more secrets `UNSET`; nothing was contacted |
| `3`  | `BLOCK` — at least one endpoint failed (auth, timeout, non-2xx) |
| `4`  | `ERROR` — runtime prerequisite missing (`curl`) |
| `5`  | `BLOCK` — endpoint tokens are equal or an endpoint accepted the other endpoint's token |

### Evidence rows

Fill the table below from a successful (`exit 0`) run. Copy the script's
own `host=` and `http_code=` lines verbatim. Do NOT paste the response
body, the request id, or any header value.
Canonical smoke procedure: manually dispatch `Modal Runtime Activation`
(`.github/workflows/modal-runtime-activation.yml`) with endpoint smoke enabled. Do not reference or run any other smoke workflow unless repository discovery confirms it is the intended active workflow for that run. A successful endpoint smoke returns `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION`, uses `BAYYINAH_API_TOKEN` for Bayyinah and `MIHWAR_API_TOKEN` for Mihwar, rejects each endpoint's opposite token, shows no `*.modal.run` string in any log line, and records no response bodies. Record the run URL + UTC timestamp in the Evidence column and flip the verdict to `VERIFIED` only after that successful smoke evidence exists.

| Agent      | Endpoint reachable | Verdict roundtrip | Evidence |
|------------|--------------------|-------------------|----------|
| Bayyinah   | SKIPPED_UNVERIFIED | SKIPPED_UNVERIFIED | PR #221 (merged 2026-05-23) auto-triggered agent-review.yml; bayyinah-review job completed in 10 s with conclusion `success` — diagnostic signature of absent secret per `secrets-policy.md §3.1`, not a live response |
| Mihwar     | SKIPPED_UNVERIFIED | SKIPPED_UNVERIFIED | PR #221 mihwar-fix job conclusion `skipped` (Bayyinah verdict ≠ REQUEST_CHANGES); no direct probe attempted |

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
| SECRET_MISSING    | BAYYINAH_ENDPOINT, MIHWAR_ENDPOINT, BAYYINAH_API_TOKEN, MIHWAR_API_TOKEN not set; expected outside CI/runtime | Awaiting operator follow-up to configure deployment secrets and run `.github/workflows/modal-runtime-activation.yml` with smoke enabled; launch evidence remains UNVERIFIED until `VERIFIED_ENDPOINT_SMOKE_AND_TOKEN_ISOLATION` is observed |
| SHARED_TOKEN      | BAYYINAH_API_TOKEN equals MIHWAR_API_TOKEN, or a live endpoint accepts the other endpoint's token | Provision distinct endpoint tokens and re-run smoke; `BLOCKED_SHARED_ENDPOINT_TOKEN` is not launch evidence |
| TEST_FAILURE      | PARTIAL — targeted Modal/token and Node unit checks pass; full Python suite is environment-blocked here by missing `httpx`/`requests` | Re-run after installing declared Python test dependencies |

## 8. Sign-off

Sign-off is only valid if every P0 row above is filled with non-`PENDING`
evidence and the latest COMMANDER REPORT verdict is `READY`.

- Operator: PENDING (requires human approval after runtime verification)
- Date: PENDING
- COMMANDER REPORT verdict: LOCAL_READY — all local P0 gates pass; runtime verification blocked on secrets
