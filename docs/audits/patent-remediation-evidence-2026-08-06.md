# Patent Remediation Evidence — 2026-08-06

> **CONFIDENTIAL — INTERNAL IP WORK PRODUCT**
> Follow-up to `docs/audits/patent-verification-audit-v2.md` and
> `docs/operations/patent-portfolio-remediation-roadmap-2026-05-24.md`.
> Do not copy patent claim details into public-facing surfaces.

## Scope

Executes roadmap Priority 1 (PAT-001) and three items of Priority 2
(PAT-003, PAT-004, PAT-014) inside `CurLexAI/swarms`. Statuses below use
the repository evidence-label contract; runtime deployment evidence
remains `SKIPPED_UNVERIFIED` (no Modal secrets in this environment), so
no patent is promoted to STRONG in this pass — STRONG requires the
runtime marker per the roadmap.

## PAT-001 — Bayyinah Truth Verification Engine (was MEDIUM)

- code_evidence: `.agents/validators/bayyinah_truth_gate.py` — TruthGate
  (verdict APPROVE/REQUEST_CHANGES/BLOCKED over evidence-labelled
  claims), AuditTrail integration (`evaluate_and_audit` → Qal'a Q7
  sealed sink, sanitized payload), LLM Bridge seam (`LLMBridge` protocol,
  `OfflineLLMBridge` default, `resolve_bridge` refuses
  `ALLOW_EXTERNAL_AI=true`). VERIFIED.
- test_evidence: `tests/test_bayyinah_truth_gate.py` (13 tests, passing).
  VERIFIED.
- runtime_evidence: SKIPPED_UNVERIFIED (needs Modal deployment marker).
- actual_status: **MEDIUM→STRONG-candidate** — all three claim elements
  (TruthGate + AuditTrail + LLM Bridge) now exist by name with tests;
  only the runtime marker is outstanding.

## PAT-003 — Sovereign-First Model Routing (was WEAK)

- code_evidence: `.agents/router/model_policy_engine.py` —
  `DataClassification` enum (+ claim-language alias
  `DATA_CLASSIFICATION`), `select_provider_by_classification()` (+ alias
  `selectProviderByClassification`), `PERMANENTLY_BLOCKED_PROVIDERS`
  frozenset excluded unconditionally for every classification. VERIFIED.
- test_evidence: `tests/test_model_policy_classification.py` (10 tests,
  passing; includes fail-closed and permanent-block coverage). VERIFIED.
- runtime_evidence: SKIPPED_UNVERIFIED.
- actual_status: **MEDIUM** — claim elements now exist as named;
  production routing decisions not yet evidenced by a CI artifact
  (see `docs/operations/sovereign-audit-readiness-certification.md`
  required-evidence list).

## PAT-004 — Cascaded ML Security Gate (was WEAK)

- code_evidence: `.agents/validators/qala_ml_cascade.py` —
  `CascadedSecurityGate` with ordered pluggable stages
  (`codebert-code-threat`, `modernbert-prompt-injection`,
  `bert-small-ksa-pii` slots), SAFE/WARNING/BLOCKED verdicts,
  short-circuit on BLOCK, measured per-scan latency against the 200ms
  CPU budget. VERIFIED.
- test_evidence: `tests/test_qala_ml_cascade.py` (13 tests, passing).
  VERIFIED.
- runtime_evidence: SKIPPED_UNVERIFIED.
- actual_status: **MEDIUM (architecture)** — the cascade contract,
  verdict set, and latency budget are implemented and tested; the
  default stage classifiers are deterministic rule-based fallbacks.
  Binding actual CodeBERT/ModernBERT/BERT-small runtimes is a
  deployment step gated by `dependency-build-safety.md` (no model
  downloads in-repo) and remains open before this claim element is
  fully satisfied. Do not represent the ML-model element as implemented.

## PAT-014 — Auditable Reasoning Chain (was WEAK)

- code_evidence: `.agents/validators/reasoning_chain.py` —
  `ReasoningChainBuilder` (direct + middleware `record()` form,
  append-only, one-way sealed) and `DecisionCertificate` carrying the
  SHA-256 of the canonical full chain; `verify_certificate` detects
  mutation, reorder, truncation, and decision substitution;
  `certificate_audit_payload` bridges to the Qal'a sink. VERIFIED.
- test_evidence: `tests/test_reasoning_chain.py` (15 tests, passing).
  VERIFIED.
- runtime_evidence: SKIPPED_UNVERIFIED.
- actual_status: **MEDIUM→STRONG-candidate** — both named claim
  elements exist with tamper-evidence tests; runtime marker outstanding.

## Unchanged in this pass

- PAT-007, PAT-010 remain WEAK (Priority 2 remainder).
- PAT-002, PAT-006, PAT-008, PAT-009, PAT-013 remain MISSING
  (Priority 4 — architectural intake required first).
- PAT-005, PAT-018 remain OUT_OF_SCOPE (LexPrim/Qarar monorepo).

## LexPrim location verification (roadmap Priority 3)

BLOCKED — no repository named `LexPrim` exists under the CurLexAI
GitHub organization accessible to this environment (checked
2026-08-06; available: `swarms`, `FRONT`, and archived template
repos). The canonical LexPrim/Qarar code location for PAT-005 and
PAT-018 remains undocumented; until it is identified, their
OUT_OF_SCOPE evidence cannot be collected.

## Verification commands (all run 2026-08-06, all passing)

```bash
python3 -m pytest -q tests/          # 451 passed, 6 skipped
python3 .agents/validate.py          # VALIDATION: PASS
bash scripts/commander/adr-0001-boundary-gate.sh .   # PASS
bash scripts/commander/p0-security-test-gate.sh .    # PASS (69 tests)
bash scripts/commander/modal-boundary-gate.sh .      # PASS
bash scripts/commander/qala-audit-integrity-gate.sh . # PASS
```

## Governance

- No external filing readiness is claimed: STRONG remains 0 until
  runtime markers exist and the verification audit is re-run.
- Re-run `docs/audits/patent-verification-audit-v2.md` methodology
  against this baseline and update its summary before any external
  claim.
