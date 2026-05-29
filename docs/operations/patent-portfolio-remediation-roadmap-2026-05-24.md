# Patent Portfolio Remediation Roadmap (2026-05-24)

> **CONFIDENTIAL — INTERNAL IP WORK PRODUCT**
> Baseline planning artifact derived from `docs/audits/patent-verification-audit-v2.md`.
> For internal execution and legal readiness tracking only.

## Baseline (from verification audit)

| Status | Count | Percent |
|---|---:|---:|
| STRONG | 0 | 0.0% |
| MEDIUM | 1 | 7.7% |
| WEAK | 5 | 38.5% |
| MISSING | 7 | 53.8% |
| OUT_OF_SCOPE | 2 | 15.4% |

## Executive Decision
- Do not proceed with external filing based on this repository baseline alone.
- Treat `STRONG=0` as a hard readiness blocker.
- Use PAT-001 as the first remediation candidate to prove MEDIUM→STRONG path.

## Priority Queue

### Priority 1 — PAT-001 (MEDIUM → STRONG)
Target: add explicit TruthGate + LLM bridge implementation evidence and passing tests; then collect runtime deployment marker.

### Priority 2 — WEAK cluster (PAT-003, PAT-004, PAT-007, PAT-010, PAT-014)
Target: convert partial/scaffold evidence into concrete implementation evidence with direct tests.

### Priority 3 — OUT_OF_SCOPE verification (PAT-005, PAT-018)
Target: verify and document canonical code location in LexPrim/Qarar repository.

### Priority 4 — MISSING cluster (PAT-002, PAT-006, PAT-008, PAT-009, PAT-013)
Target: architectural intake and phased implementation plan.

## Modal Cost Control Policy (Immediate)
Default operating mode for routine repository work: `LOCAL_ONLY`.

- LOCAL_ONLY: no Modal invocation for simple/repetitive skill tasks.
- HYBRID_ON_DEMAND: allow Modal only when task explicitly depends on Mihwar/Bayyinah output.
- MODAL_REQUIRED: deployment smoke checks/incidents only.

## 6-Week Delivery Plan

| Week | Focus | Expected Output |
|---|---|---|
| 1-2 | PAT-001 uplift | PAT-001 promoted to STRONG (code + tests + runtime marker) |
| 3-4 | PAT-003 + PAT-004 uplift | both moved from WEAK toward MEDIUM |
| 5 | PAT-005 + PAT-018 location verification | out-of-scope evidence report with repository references |
| 6 | MISSING cluster intake | implementation briefs and sequencing for remaining patents |

## Governance Notes
- Keep patent detail documents internal-only.
- Avoid public claims that all patents are implemented until evidence reaches STRONG per patent.
- Re-run verification audit after each phase and update the status matrix.
