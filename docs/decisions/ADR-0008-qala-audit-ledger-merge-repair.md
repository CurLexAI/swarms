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
4. **Structural fix (Implemented).** The merge guard stops silent corruption
   but does not address the root cause (a hash-chain tracked in git) or the
   tail-truncation gap. Both are now implemented:

   - **(A) Ledger no longer tracked in git — sealed from a merge-safe source.**
     `artifacts/security/qala-audit.jsonl` is removed from tracking and
     gitignored. The committed source is `artifacts/security/qala-audit.events.json`
     — a plain JSON **array of events** (`recordId`, `event`, `traceId`,
     `spanId`, `tenantId`, `occurredAt`, `payload`) with **no `prevHash`/
     `recordHash`**. A positional hash-chain is what git merges corrupt; an
     unordered-by-hash event array cannot be silently concatenated into a
     broken chain (a merge that duplicates an element is a visible,
     reviewable JSON diff, not a hidden chain break). A new `seal` command
     (`QalaAuditSink.seal_from_events` / `QalaAuditSink.sealFromEvents`)
     deterministically rebuilds the sealed `.jsonl` from this source: because
     each event carries a stable `recordId` + `occurredAt`, re-sealing is
     **byte-reproducible**. `qala-audit-integrity-gate.sh` now seals from the
     event source before verifying, and CI (`.github/workflows/main.yml`)
     uploads the sealed chain as a build artifact (`qala-audit-chain`).
   - **(B) Tail-truncation gap closed via a sealed anchor.** A committed
     `artifacts/security/qala-audit.anchor.json` pins `recordCount` and
     `headHash`. `verify_chain` / `verifyChain` now accept an expected count
     and head hash and **fail** when either the walked record count or the
     final head hash diverges from the anchor. Removing the last *N* records
     leaves a still-link-valid prefix (which the old forward-only walk
     passes), but it changes both the count and the head hash, so the anchor
     now catches it. Unit tests on both runtimes assert that the unanchored
     walk still passes the truncated prefix (demonstrating the gap) while the
     anchored verify fails.

   **Honesty caveat.** A git/CI-sealed ledger is **tamper-evident in review**,
   not tamper-proof: anyone with repo-write could edit the event source and
   re-anchor in the same commit. The anchor makes tamper/truncation visible
   in the diff and breaks any sealed chain that does not match a committed
   anchor; true immutability would require append-only runtime storage and is
   out of scope.

## Consequences

- The Q7 chain stays verifiable in CI; PRs are not blocked by pre-existing
  merge corruption on `main`.
- The ledger reflects genuine event history (no phantom duplicate events).
- Future merges that touch the ledger conflict instead of silently
  concatenating (the `-merge` guard), so the duplicate/broken-link
  corruption stops recurring automatically and is surfaced for a deliberate
  re-seal.
- The tail-truncation gap is closed: `verify_chain` now enforces a sealed
  record count and head hash from `qala-audit.anchor.json`, so removing
  trailing records (a still-link-valid prefix) fails the gate.
- The ledger is no longer tracked in git; the merge-safe `qala-audit.events.json`
  source plus the `qala-audit.anchor.json` anchor are tracked instead, and the
  sealed chain is regenerated deterministically by the gate and in CI. This
  removes the structural cause of the recurring merge corruption (a positional
  hash-chain stored in git).
- Hand-edits to this file remain prohibited **except** for the narrow
  merge-repair case authorised here, which must cite this ADR.
