# Security Triage — CurLexAI/swarms — 2026-06-28

## Scope

Focused security review of `CurLexAI/swarms` as an agent operations repository.
Applied prior security/compliance direction: tighten posture, reduce policy drift, preserve low blast radius.

## Evidence Labels

- `VERIFIED` — confirmed by command output or file inspection in this session
- `INFERRED` — reasonable conclusion from available evidence
- `UNVERIFIED` — not checked or blocked by missing access/secrets/runtime

---

## Gates Run

| Gate | Result | Notes |
|---|---|---|
| `p0-security-test-gate.sh` | VERIFIED PASS | 69 tests OK |
| `modal-boundary-gate.sh` | VERIFIED PASS | After fix (see below) |
| `adr-0001-boundary-gate.sh` | VERIFIED PASS | No boundary drift |
| `agent-presence-gate.sh` | VERIFIED PASS (WARN) | Missing runtime secrets — expected outside CI |
| `qala-audit-integrity-gate.sh` | VERIFIED PASS | 14 Qala tests OK |
| `qala-egress-residency-gate.sh` | VERIFIED PASS | No unapproved egress hosts |
| `static_audit.py` | VERIFIED PASS | No obvious secrets detected |
| `python3 -m pytest tests/` | VERIFIED — 308 passed, 4 skipped | 4 test files skipped (pydantic/anyio/httpx not installed) |

---

## Findings

### CRITICAL — Modal endpoint URLs committed in tracked example file

**File:** `.agents/mcp/cloudflare-mcp/.env.example`

**Before:**
```
MIHWAR_ENDPOINT="https://curlexai--mihwar-generate.modal.run"
BAYYINAH_ENDPOINT="https://curlexai--bayyinah-review.modal.run"
```

Real `*.modal.run` URLs were committed in a tracked Git file. This violates:
- `secrets-boundary.md` — example files must use placeholders only
- `modal-boundary-gate.sh` intent — Modal endpoints are backend-only and must not appear in tracked files
- `ADR-0003` — Qala architecture prohibits Modal surface leakage

**Status:** VERIFIED FIXED in this session.

---

### HIGH — `modal-boundary-gate.sh` gap: did not scan `.env.example` files

The gate scanned only `src`, `public`, and build-artifact directories. The `.agents/mcp/cloudflare-mcp/.env.example` leak was not caught by the gate.

**Status:** VERIFIED FIXED — added section 5b to `modal-boundary-gate.sh` that scans all tracked `.env.example` files for committed `*.modal.run` URLs.

---

### MEDIUM — Inconsistent placeholder style in MCP example files

**Files:**
- `.agents/mcp/.env.example` — used commented-out blank (`# QARAR_API_TOKEN=`)
- `.agents/mcp/modal-mcp/.env.example` — used `replace-me` placeholders
- `.agents/mcp/cloudflare-mcp/.env.example` — used `"replace-with-..."` strings

Inconsistent placeholders reduce clarity; developers may not recognize `replace-me` as a required secret.

**Status:** VERIFIED FIXED — all standardized to `__SET_IN_SECRET_STORE__` matching the main `.env.example` convention.

---

## Controls Verified Intact

| Control | Status |
|---|---|
| Aegis MCP gateway (role-based tool filtering + prompt injection) | VERIFIED present and tested |
| Qala input gate (prompt injection, PII, tenant isolation) | VERIFIED present and tested |
| Qala audit sink (hash-chained append-only log) | VERIFIED integrity gate passes |
| ****** auth (`verify_bearer_token` in `runtime_security.py`) | VERIFIED — HMAC compare_digest, no shared-token fallback |
| Qdrant auth (`require_qdrant_auth`) | VERIFIED — fail-closed; production enforces API key |
| Model pinning (`require_pinned_revision`) | VERIFIED — full 40-char SHA required |
| Supply-chain remote code guard (`trust_remote_code_for`) | VERIFIED — dual-key: pinned SHA + explicit ACK env var |
| ADR-0001 boundary enforcement | VERIFIED — no forbidden paths, no autoStart flags |
| Egress residency | VERIFIED — no unapproved outbound hosts |
| CORS | VERIFIED — main `.env.example` uses explicit allowlist; MCP example now documented |

---

## Remaining Risks

| Risk | Severity | Status |
|---|---|---|
| 4 test files require pydantic/anyio/httpx not in base environment | MEDIUM | UNVERIFIED if CI `requirements-agent.txt` covers them — review CI `main.yml` |
| Modal secrets (`MIHWAR_ENDPOINT`, `MIHWAR_API_TOKEN`, etc.) absent from this environment | LOW | Expected; WARN is not a FAIL per gate design |
| `QARAR_API_TOKEN` in `.agents/mcp/.env.example` newly documented as required in production | LOW | Follow-up: ensure deployment runbooks reference this requirement |

---

## Changes Made

| File | Change | Reason |
|---|---|---|
| `.agents/mcp/cloudflare-mcp/.env.example` | Removed real `*.modal.run` URLs; standardized all placeholders to `__SET_IN_SECRET_STORE__` | CRITICAL — Modal URL committed in tracked file |
| `.agents/mcp/.env.example` | Added production override note for `ALLOW_ORIGINS`; documented `QARAR_API_TOKEN` as required in production; standardized placeholder | MEDIUM — policy clarity |
| `.agents/mcp/modal-mcp/.env.example` | Standardized `replace-me` and `<server-side-*>` placeholders to `__SET_IN_SECRET_STORE__`; improved endpoint comment | MEDIUM — policy clarity |
| `scripts/commander/modal-boundary-gate.sh` | Added section 5b: scan all tracked `.env.example` files for committed `*.modal.run` URLs | HIGH — close gate gap that missed the CRITICAL finding |
| `docs/audits/security-triage-2026-06-28.md` | This file | Audit trail |

---

## Validation Evidence

```
[P0] Running Bayyinah + Router + Aegis MCP security test gate
Ran 69 tests in 0.040s — OK

modal-boundary-gate.sh — RESULT: PASS
  [OK] no *.modal.run URL committed in tracked example files  (NEW CHECK)

python3 -m pytest tests/ — 308 passed, 4 skipped
```

---

## Next Highest-Value Actions

1. Ensure `requirements-agent.txt` covers `pydantic`, `anyio`, `httpx` so the 4 skipped test files run in CI.
2. Verify deployment runbooks reference `QARAR_API_TOKEN` as a mandatory production secret.
3. Schedule quarterly re-run of this triage against any new `.env.example` files added to the repo.
