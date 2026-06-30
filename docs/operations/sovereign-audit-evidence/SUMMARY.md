# Sovereign Air-Gap & Egress-Residency Audit — Evidence Summary

- Repository: `CurLexAI/swarms`
- Mode: **Sovereign offline** — `ALLOW_EXTERNAL_AI` and `CORE_SWARM_ENABLE_LIVE_CALLS` were left **unset** for every command. No external AI egress was enabled at any step.
- Each command in this directory has its own evidence file capturing the full `stdout`+`stderr`, the working directory, the sovereign-mode env state, the exit code, and a `RESULT: PASS|FAIL` line.

> Evidence label convention (per `AGENTS.md`): `VERIFIED` = confirmed by command output / file content; `SKIPPED_UNVERIFIED` = blocked by a missing secret/runtime, not a real failure; `PRE-EXISTING FAIL` = failure present on a clean checkout, unrelated to sovereignty/egress and not introduced by this change.

## Task 1 — Execution & evidence

| Command | Evidence file | Result | Classification |
|---|---|---|---|
| `bash scripts/commander/release-readiness-gate.sh .` | `release-readiness-gate.txt` | FAIL | PRE-EXISTING FAIL — chains the Qal'a audit-integrity gate, which fails on the sealed ledger (see below). Not a sovereignty/egress issue. |
| `bash scripts/commander/qala-egress-residency-gate.sh .` | `qala-egress-residency-gate.txt` | **PASS** | Q8 egress residency clean — no unapproved hosts in `.agents/src/scripts/sama_ingestion_swarm`. |
| `bash scripts/commander/master-audit-gate.sh .` | `master-audit-gate.txt` | **PASS** | Aggregate sovereignty/boundary gate passes. |
| `bash scripts/commander/modal-boundary-gate.sh .` | `modal-boundary-gate.txt` | **PASS** | No `*.modal.run`/SDK leak into client surfaces (missing runtime secrets WARN only). |
| `bash scripts/commander/adr-0001-boundary-gate.sh .` | `adr-0001-boundary-gate.txt` | **PASS** | No forbidden product paths / `autoStart` flags. |
| `bash scripts/commander/public-surface-boundary-gate.sh .` | `public-surface-boundary-gate.txt` | **PASS** | Public surface boundary clean. |
| `bash scripts/commander/p0-security-test-gate.sh .` | `p0-security-test-gate.txt` | **PASS** | P0 Bayyinah + router + Aegis MCP security tests pass. |
| `bash scripts/commander/agent-presence-gate.sh .` | `agent-presence-gate.txt` | **PASS** | Required agent assets present (missing endpoint secrets WARN only). |
| `bash scripts/commander/agent-activation-preflight.sh .` | `agent-activation-preflight.txt` | FAIL | SKIPPED_UNVERIFIED — fails only on `missing env: MODAL_TOKEN_ID`. Expected outside CI/runtime; **not** a sovereignty failure. |
| `bash scripts/commander/repo-rename-gate.sh .` | `repo-rename-gate.txt` | FAIL | PRE-EXISTING FAIL — greps the literal strings `AUTH_MISSING` / legacy repo names (`CurLexAI/LexPrim`, `LexBANK/BSM`, `MOTEB1989/LexPrim`) that already exist in tracked `docs/` and `scripts/`. Unrelated to sovereignty/egress. |
| `bash scripts/commander/qala-audit-integrity-gate.sh .` | `qala-audit-integrity-gate.txt` | FAIL | PRE-EXISTING FAIL — the TS + Python chain *unit tests* pass; only the sealed ledger `artifacts/security/qala-audit.jsonl` fails verification: `AUDIT_CHAIN_BROKEN at_record=1` (record 1 `prevHash` is `GENESIS` instead of record 0's `recordHash`). Per `AGENTS.md`/`CLAUDE.md` this artifact must not be hand-edited. Not a sovereignty/egress issue. |
| `python3 scripts/commander/swarm-presence-monitor.py --repo-root . --no-network` | `swarm-presence-monitor.txt` | **PASS** | Offline presence monitor verifies static controls. |
| `python3 scripts/verify_aegis.py` | `verify_aegis.txt` | **PASS** | Full Aegis gate green (see Task 3). |
| `python3 .agents/validate.py` | `validate.txt` | **PASS** | 7 required agent files validated. |
| `python3 .agents/invoke.py info` | `invoke-info.txt` | **PASS** | Agent inventory listed, no secrets needed. |
| `python3 -m pytest -q tests/` | `pytest.txt` | **PASS** | 373 passed, 6 skipped (skips are secret/runtime-gated, **not** network failures). |
| `npm run check` | `npm-check.txt` | FAIL | PRE-EXISTING FAIL — every step (service-divergence, unit tests, ADR-0001, CDN SRI, runtime-policy, …) passes; it fails only at the Qal'a audit-integrity step on the same `AUDIT_CHAIN_BROKEN` ledger issue above. |
| `npx tsc --noEmit` | `tsc-noemit.txt` | **PASS** | The TS blocker documented in `AGENTS.md` (TS2345/TS18046/TS2352 in `unifiedAgentAdapter.ts`) **did not reproduce** — 21 `src/` files type-checked clean (a recent refactor resolved it). Recorded as PASS, not a sovereignty concern either way. |

### No external-network test failures
The full Python suite ran fully **offline** and passed (373 passed, 6 skipped). The 6 skips are gated on missing secrets/runtime, not on outbound network calls. **No test required external network access**, so there is no fail-closed (egress) violation to remediate in the test suite.

### Genuine failures, all out of sovereignty scope
None of the 5 FAILs are sovereignty/air-gap/egress violations:
- `agent-activation-preflight` → missing `MODAL_TOKEN_ID` secret (SKIPPED_UNVERIFIED).
- `qala-audit-integrity` (and therefore `release-readiness` and `npm run check`, which chain it) → pre-existing broken sealed audit ledger `artifacts/security/qala-audit.jsonl`. The audit-chain *logic* tests pass; only the committed data artifact is broken. `AGENTS.md`/`CLAUDE.md` forbid hand-editing this sealed file, so it was left untouched and is reported here as a pre-existing blocker for a separate, ADR-tracked remediation.
- `repo-rename-gate` → pre-existing literal-string matches in tracked docs/scripts.

## Task 2 — Sovereignty-gate ordering hardening (CHANGED)

In `.agents/providers/openai_provider.py` and `.agents/providers/anthropic_provider.py`, `execute()` previously checked the API key **before** the `ALLOW_EXTERNAL_AI` flag. The order is now **flag → key → transport**:

```python
def execute(self, request):
    if os.environ.get("ALLOW_EXTERNAL_AI", "").lower() != "true":
        raise RuntimeError("ALLOW_EXTERNAL_AI=true is required before using <X> route.")
    api_key = os.environ.get("<X>_API_KEY", "")
    if not api_key:
        raise RuntimeError("<X>_API_KEY is not configured; <X> route is unavailable.")
    raise NotImplementedError(...)   # unchanged — transport intentionally absent
```

This makes the "no-egress" decision independent of (and prior to) any credential consideration — strict fail-closed. The final `NotImplementedError` is preserved (transport is intentionally unimplemented in this governance repo).

**Test contract updated to match:** `tests/test_external_provider_guards.py` previously pinned the *old* `key → flag` order (`test_missing_api_key_raises_runtime_error` ran with an empty env and asserted `"not configured"`). Under the new order an empty env now correctly raises on the `ALLOW_EXTERNAL_AI` gate first. The test was updated to faithfully encode `flag → key → transport` with equally strict assertions:
- new `test_sovereignty_gate_runs_before_key_check` — empty env (no flag, no key) must raise on `ALLOW_EXTERNAL_AI`, proving the gate runs before the key check;
- `test_missing_api_key_raises_runtime_error` — now sets `ALLOW_EXTERNAL_AI=true` (no key) and asserts `"not configured"`, proving the key gate still fires once egress is allowed.

Result: `tests/test_external_provider_guards.py` → 16 passed; full suite → 373 passed, 6 skipped.

## Task 3 — Enforcement files under `src/policy/sovereign`

`scripts/verify_aegis.py` (`CORE_DIR = src/policy/sovereign`) and a direct inspection both confirm:

| File | Present |
|---|---|
| `classification.py` | **PASS** |
| `model_router.py` | **PASS** |
| `audited_router.py` | **PASS** |
| `provider_interface.py` | **PASS** |

`model_router.py` controls (verified by `verify_aegis.py` and by direct grep/read):

| Control | Result | Evidence |
|---|---|---|
| Blocks when local providers are unavailable instead of falling through to an external provider (`BLOCKED_LOCAL_PROVIDER_UNAVAILABLE`) | **PASS** | `route()` iterates only the local providers from `provider_order_for_classification()` (Ollama / llama.cpp) and, when all fail, returns `_blocked_decision(...)` with `blocked_reason="BLOCKED_LOCAL_PROVIDER_UNAVAILABLE"`. No external fallback path exists. |
| Embeds no external AI provider endpoints | **PASS** | 0 matches for `api.openai.com` / `api.anthropic.com` / `generativelanguage.googleapis.com` / `vertexai.googleapis.com`. The only `external` token is a docstring stating "No external providers are ever returned". |
| Does not read `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | **PASS** | 0 matches for either name. |

No fail-closed break (e.g. a local→external fallthrough) was found, so **no edits were made to enforcement logic** under `src/policy/sovereign`.

---

```text
=== COMMANDER REPORT ===
Mission: Prove sovereign air-gap / egress residency via gates + evidence; harden provider sovereignty-gate order; verify src/policy/sovereign enforcement.
Repository: CurLexAI/swarms
Branch: devin/<ts>-sovereign-audit
Priority: P1 (sovereignty / fail-closed)
Owner: Codex Commander
Status: PARTIAL_PASS

VERIFIED:
- All sovereignty/egress gates PASS offline: qala-egress-residency, master-audit, modal-boundary, adr-0001, public-surface, p0-security, verify_aegis (incl. env-egress), swarm-presence.
- Python suite passes fully offline (373 passed, 6 skipped); no test needs external network — no fail-closed violation.
- Provider sovereignty gate reordered to flag -> key -> transport in openai_provider.py and anthropic_provider.py; final NotImplementedError preserved.
- src/policy/sovereign enforcement files present; model_router blocks on local-unavailable, embeds no external endpoints, reads no external API keys.

SKIPPED_UNVERIFIED:
- agent-activation-preflight: missing MODAL_TOKEN_ID (expected outside CI/runtime).
- 6 pytest skips: secret/runtime-gated, not network.

UNVERIFIED / PRE-EXISTING (out of sovereignty scope):
- qala-audit-integrity / release-readiness / npm run check: sealed ledger artifacts/security/qala-audit.jsonl AUDIT_CHAIN_BROKEN at record 1 (must not be hand-edited).
- repo-rename-gate: literal AUTH_MISSING / legacy repo names in tracked docs.

CHANGED:
- .agents/providers/openai_provider.py, .agents/providers/anthropic_provider.py (gate order).
- tests/test_external_provider_guards.py (contract updated to flag -> key -> transport).
- docs/operations/sovereign-audit-evidence/ (this evidence set).

VALIDATION:
- command: python3 -m pytest -q tests/    result: PASS    evidence: pytest.txt (373 passed, 6 skipped)
- command: python3 scripts/verify_aegis.py result: PASS    evidence: verify_aegis.txt
- command: bash scripts/commander/qala-egress-residency-gate.sh . result: PASS evidence: qala-egress-residency-gate.txt

RISKS:
- CRITICAL: none introduced by this change.
- HIGH: none.
- MEDIUM: pre-existing AUDIT_CHAIN_BROKEN in sealed ledger blocks release-readiness/npm-check (separate ADR-tracked remediation).
- LOW: repo-rename-gate literal-string false positives.

DECISION: REQUEST_CHANGES (sovereignty objectives met; pre-existing ledger/repo-rename failures owned separately).
NEXT ACTION: Open PR with provider hardening + evidence; flag the pre-existing AUDIT_CHAIN_BROKEN ledger and repo-rename-gate matches for a dedicated follow-up.
===
```
