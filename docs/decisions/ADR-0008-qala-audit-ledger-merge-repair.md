# ADR-0008 — Qal'a Audit Ledger Merge-Repair (de-duplicate + re-seal) Exception

- **Status:** Accepted (one-time repair + standing exception procedure)
- **Decision date:** 2026-06-30
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none
- **Relates to:** ADR-0003 (Qal'a security architecture, §Q7 audit sink)

## Context

`artifacts/security/qala-audit.jsonl` is the Qal'a (Q7) append-only,
SHA-256 hash-chained audit sink. CLAUDE.md and AGENTS.md document it as
"sealed … do not hand-edit", and `scripts/commander/qala-audit-integrity-gate.sh`
(wrapping `QalaAuditSink.verify_chain`) enforces forward-link integrity in CI.

The ledger is **tracked in git**. Because git has no awareness of the
append-only invariant, branch merges that touch the file concatenate the
two sides. This has repeatedly produced a corrupt on-disk chain:

1. **Multiple GENESIS roots / broken links.** A merge concatenated three
   independently-sealed chains, so `verify_chain` failed at record 1
   (`prev_hash mismatch`). This pre-existed on `main` and was repaired by
   the previously-merged re-seal `d6011ac`, and again during PR #409.
2. **Duplicated event records.** The `Merge branch 'main'` commit
   `d9252a4` (in PR #409) concatenated two copies of the same log, leaving
   16 records of which only **9 were unique**. Each of the 7 duplicates is
   identical to an earlier record on every *event/content* field —
   `recordId`, `occurredAt` (to the microsecond), `event`, `traceId`,
   `spanId`, `tenantId`, and `payload` — although their `prevHash`/
   `recordHash` differ, because the duplicate copies were re-linked into
   later chain positions during the PR #409 re-seal (`be19809`). A reused
   `recordId` paired with an identical microsecond `occurredAt` cannot be
   produced by `QalaAuditSink.append()` (fresh `uuid4()` + fresh timestamp
   per call), nor by a replay through it (a replay mints new ids and
   timestamps). The only mechanism that reproduces the same
   `recordId`+`occurredAt`+`payload` is file-level duplication during a git
   merge — i.e. they are merge artifacts, not genuine distinct audit
   events.

Automated review correctly flagged both states: the duplicates as a defect,
and the deletion of sealed lines as an append-only/tamper concern. The
forward-only `verify_chain` cannot, by design, detect tail truncation, so a
green gate alone does not prove "no records were removed."

## Decision

1. **One-time repair (PR #412).** Collapse the 7 merge-duplicate records
   (matched by event/content fields) and re-seal the chain over the 9
   genuine events, in original
   order, using the sink's own `_canonicalize`/`_sha256` (record 0 =
   GENESIS, each later `prevHash` = prior `recordHash`). No genuine event's
   payload, id, or timestamp is altered; the diff is a pure deletion of
   duplicated lines. This is a deliberate, evidence-bound repair of
   merge-induced corruption, **not** a content edit or a removal of genuine
   audit evidence — it is the documented exception this ADR authorises.
2. **Standing exception.** Repairing the ledger to undo *merge-induced*
   corruption (multi-GENESIS concatenation or duplicated event records) is
   a permitted maintenance operation, provided it: (a) preserves every
   unique event verbatim, (b) re-seals via the sink's own canonicalize/hash
   functions, and (c) is recorded against this ADR in the PR.
3. **Merge guard (this PR).** `.gitattributes` now marks the ledger
   `-merge -text`, so git refuses to auto-merge it: a branch that diverges
   from `main` on this file raises a **conflict** instead of silently
   concatenating two sealed chains (the cause of the duplicate records and
   broken links above). On conflict, the operator deliberately re-seals
   under this ADR rather than letting git union-merge. `diff` stays enabled
   so the file remains reviewable in PRs.
4. **Structural follow-up (recommended, separate PR).** The merge guard
   stops silent corruption but does not make the ledger tamper-proof against
   deliberate edits. The durable fix is to stop tracking a tamper-evident
   ledger in git at all — generate/seal it as a CI artifact — and to close
   the `verify_chain` tail-truncation gap (e.g. a sealed record-count or
   head-anchor the gate enforces).

## Consequences

- The Q7 chain stays verifiable in CI; PRs are not blocked by pre-existing
  merge corruption on `main`.
- The ledger reflects genuine event history (no phantom duplicate events).
- Future merges that touch the ledger conflict instead of silently
  concatenating (the `-merge` guard), so the duplicate/broken-link
  corruption stops recurring automatically and is surfaced for a deliberate
  re-seal.
- A residual gap remains: `verify_chain` does not detect tail truncation.
  Hardening it (e.g. a sealed record count / head-anchor) is deferred to the
  structural follow-up and is out of scope for the repair.
- Hand-edits to this file remain prohibited **except** for the narrow
  merge-repair case authorised here, which must cite this ADR.
