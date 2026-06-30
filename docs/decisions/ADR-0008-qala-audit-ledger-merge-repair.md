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
2. **Byte-identical duplicate records.** The `Merge branch 'main'` commit
   `d9252a4` (in PR #409) concatenated two copies of the same log, leaving
   16 records of which only **9 were unique**. The 7 duplicates were
   identical on *every* field — `recordId`, `occurredAt` (to the
   microsecond), and `recordHash`. Such records cannot be produced by
   `QalaAuditSink.append()` (fresh `uuid4()` + fresh timestamp per call),
   nor by a replay through it (a replay mints new ids/timestamps). The
   only mechanism that reproduces byte-identical lines is file-level
   duplication during a git merge — i.e. they are merge artifacts, not
   genuine distinct audit events.

Automated review correctly flagged both states: the duplicates as a defect,
and the deletion of sealed lines as an append-only/tamper concern. The
forward-only `verify_chain` cannot, by design, detect tail truncation, so a
green gate alone does not prove "no records were removed."

## Decision

1. **One-time repair (PR #412).** Collapse the 7 byte-identical merge
   duplicates and re-seal the chain over the 9 genuine events, in original
   order, using the sink's own `_canonicalize`/`_sha256` (record 0 =
   GENESIS, each later `prevHash` = prior `recordHash`). No genuine event's
   payload, id, or timestamp is altered; the diff is a pure deletion of
   duplicated lines. This is a deliberate, evidence-bound repair of
   merge-induced corruption, **not** a content edit or a removal of genuine
   audit evidence — it is the documented exception this ADR authorises.
2. **Standing exception.** Repairing the ledger to undo *merge-induced*
   corruption (multi-GENESIS concatenation or byte-identical duplicates) is
   a permitted maintenance operation, provided it: (a) preserves every
   unique event verbatim, (b) re-seals via the sink's own canonicalize/hash
   functions, and (c) is recorded against this ADR in the PR.
3. **Structural follow-up (recommended, separate PR).** The durable fix is
   to stop subjecting a tamper-evident ledger to git merges — e.g. treat it
   as a CI-generated/sealed artifact rather than a merged file, and/or add a
   merge driver that refuses union-concatenation. Until then this exception
   prevents the gate from blocking unrelated PRs.

## Consequences

- The Q7 chain stays verifiable in CI; PRs are not blocked by pre-existing
  merge corruption on `main`.
- The ledger reflects genuine event history (no phantom duplicate events).
- A residual gap remains: `verify_chain` does not detect tail truncation.
  Hardening it (e.g. a sealed record count / head-anchor) is deferred to the
  structural follow-up and is out of scope for the repair.
- Hand-edits to this file remain prohibited **except** for the narrow
  merge-repair case authorised here, which must cite this ADR.
