# QARAR FULL REPOSITORY AUDIT
# Date: 2026-05-08
# Commit: 7398a98ceac5ae8c9925950f23e363afee584a6e

## EXECUTIVE SUMMARY
- Total issues: 20
- Critical (P0): 2
- High (P1): 10
- Medium (P2): 8

## SECTION 1 — REPO HEALTH

### 1.1 TypeScript/JavaScript
- P0 — `npx tsc --noEmit` failed with parser/type blocking errors in `src/services/unifiedAgentAdapter.ts` at lines 858, 891, 1006, 1020, 1075 (TS1005/TS1472). Command output captured.
- P1 — `npm test` failed; multiple tests in `tests/unifiedAgentAdapter*.test.js` failed with `Unexpected token 'export'` (ERR_TEST_FAILURE).
- P2 — `npm run validate` missing script.
- P2 — `npm run validate:registry` missing script.
- P2 — `npm run check:duplicates` missing script.
- P2 — pattern scan in `src/` for `any`, `@ts-ignore`, `eslint-disable` requires manual follow-up (no confirmed occurrences returned in current command set).

### 1.2 Python
- VERIFIED — Python compile sweep across 22 `*.py` files passed (`PY_FAILS 0`).
- BLOCKED (CONFIG_NOT_FOUND) — `backend_fastapi/` not present in this repository; `sentinel.py:14` check not executable here.
- BLOCKED (CONFIG_NOT_FOUND) — root `requirements.txt` not present for conflict inspection in requested LexPrim path.

### 1.3 Agent Registry
- VERIFIED — `agents/registry.yaml` exists.
- VERIFIED — registered agents count in YAML: 7 (`mihwar`, `bayyinah`, `qarar-router`, `deepseek-coder`, `qwen-coder`, `azure-gpt`, `gpt-o1`).
- BLOCKED (CONFIG_NOT_FOUND) — `data/agents/` directory missing.
- INFERRED drift — JSON-vs-YAML drift cannot be computed because JSON registry directory is missing.
- VERIFIED — Free Bird swarm markers not found (`fb_*` count 0, `fb_meta` absent).

### 1.4 Security
- BLOCKED (CONFIG_NOT_FOUND) — `backend_fastapi/` target missing for hardcoded-secret grep scope.
- VERIFIED — in `src/`, matches for `sk-` are regex literals inside adapter/mjs runtime artifacts; no direct hardcoded API token detected by this query.
- BLOCKED (CONFIG_NOT_FOUND) — `src/routes/` missing; auth/timing-safe/rate-limit per-route audit not executable.
- VERIFIED — `.env` entry is not present in current `.gitignore`; only Python cache/node_modules entries visible.
- VERIFIED — references to `kimi` still exist in `src/control-hub/app.js` as comments (`REMOVED` notes).

### 1.5 Architecture
- BLOCKED (CONFIG_NOT_FOUND) — `src/server.js` missing; mounted/unmounted routes analysis not executable.
- BLOCKED (UNVERIFIED_RUNTIME) — dead-file and duplicate-logic analysis for LexPrim structure cannot be proven from this repository layout.

### 1.6 Configuration
- VERIFIED — `tsconfig.json` has `"strict": true`.
- INFERRED — dependency usage audit not fully proven; `package.json` contains minimal dependencies (`js-yaml`, `uuid`, `typescript`).
- BLOCKED (CONFIG_NOT_FOUND) — `render.yaml`/Render config not located in this repository root.

## SECTION 2 — PATENT VERIFICATION

| patent_id | name | evidence_path | file_exists | code_real | imported | tested | verdict |
|---|---|---|---|---|---|---|---|
| #1 | جدار الحماية MCP | lexprim-core/patents/patent1_firewall/ | no | n/a | n/a | n/a | MISSING |
| #2 | سجل تنفيذ الوكلاء | qarar/packages/bayyinah/src/audit/ | no | n/a | n/a | n/a | MISSING |
| #3 | رسم نسب المصادر القانونية | backend_fastapi/tests/test_patent3_lineage.py | no | n/a | n/a | n/a | MISSING |
| #4 | RAG ذاتي الإصلاح | src/pipeline/qarar-rag-infra.py | no | n/a | n/a | n/a | MISSING |
| #5 | الموجّه السيادي الديناميكي | src/config/regulatory-intelligence-router.js | no | n/a | n/a | n/a | MISSING |
| #6 | بوابة الجودة + circuit breaker | search in src/ | no confirmed path | n/a | n/a | n/a | UNVERIFIED |
| #7 | اليقين BFT | qarar/packages/bayyinah/src/yaqeen/ | no | n/a | n/a | n/a | MISSING |
| #8 | سراب phantom | qarar/packages/bayyinah/src/sarab/agents/sarab-phantom.ts | no | n/a | n/a | n/a | MISSING |
| #9 | واجهة الوكلاء القانونية | qarar/packages/bayyinah/src/runner.ts + evidence.ts + authority.ts | no | n/a | n/a | n/a | MISSING |
| #10 | SPIFFE zero trust | qarar/packages/bayyinah/src/sarab/agents/sarab-arbiter.ts | no | n/a | n/a | n/a | MISSING |
| #11 | الفريق الأحمر التشريعي | qarar/packages/bayyinah/src/redteam/ | no | n/a | n/a | n/a | MISSING |
| #12 | محامي الشيطان | qarar/packages/bayyinah/src/conflict/devil-advocate.ts | no | n/a | n/a | n/a | MISSING |
| #13 | التوأم التنظيمي | qarar/packages/bayyinah/src/conflict/regulatory-twin.ts | no | n/a | n/a | n/a | MISSING |
| #14 | الذاكرة التنظيمية الجماعية | qarar/packages/bayyinah/src/conflict/collective-regulatory-memory.ts | no | n/a | n/a | n/a | MISSING |
| #15 | موجّه المحتوى التنظيمي | src/config/regulatory-intelligence-router.js | no | n/a | n/a | n/a | MISSING |
| #16 | محرك البيّنة QAR-PAT-001 | src/bayyinah/truth-gate.js + src/bayyinah/bridge.ts | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-002 | BFT | qarar/swarms/certainty/ + src/bayyinah/bft-consensus.js | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-003 | Sovereign Routing | sovereign_router.py | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-004 | Security Gate | src/security/pre-execution-gate.js | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-005 | Sector Factory | src/factory/sector-factory.js | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-008 | Legislative Watch | qarar/packages/legislative-watch/src/ | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-010 | Arabic Similarity | qarar/packages/arabic-similarity/src/ | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-013 | Legislative Watch | qarar/packages/legislative-watch/src/ | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-014 | Reasoning Chain | qarar/packages/reasoning-chain/src/ | no | n/a | n/a | n/a | MISSING |
| QAR-PAT-018 | Conflict Detector | qarar/packages/conflict-detector/src/ | no | n/a | n/a | n/a | MISSING |

## SECTION 3 — SWARMS REPO
- VERIFIED — current local repository is `CurLexAI/swarms` (`/workspace/swarms`).
- VERIFIED — top-level structure includes `.agents/`, `agents/`, `src/`, `tests/`, `docs/`, `scripts/`, `public/`.
- INFERRED — this is an operations repository, not LexPrim monorepo (matches handbook language in `AGENTS.md`).
- VERIFIED — requested LexPrim patent evidence paths are largely absent in current repo layout.
- INFERRED relationship — swarms appears to orchestrate/review agents and governance around CurLexAI runtime, while LexPrim-specific product paths are external/not present here.

## RECOMMENDED PRIORITIES
1. Resolve syntax/parser breakage in `src/services/unifiedAgentAdapter.ts` before any further runtime assertions.
2. Fix Node test module boundary causing `Unexpected token 'export'` in integration/unit suites.
3. Clarify repository targeting: run full LexPrim audit in actual LexPrim working tree (not swarms).
4. Decide policy for residual `kimi` comment markers if strict removal is required.
5. Add missing validation scripts or update audit runbook to reflect actual scripts.
