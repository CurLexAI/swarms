# ADR-0003 — Qal'a (قلعة) Sovereign Security Architecture

- **Status:** Accepted (architecture only — no runtime activation)
- **Decision date:** 2026-05-15
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none
- **Relates to:** ADR-0001 (swarms boundary), ADR-0002 (operator-static-artifacts), ADR-0002 (repo-identity)

## Context

`CurLexAI/swarms` is the agent operations and validation layer for the
CurLexAI program (ADR-0001). It carries existing security surfaces:
`bayyinah_validation_gate`, `model_policy_engine`, `sovereignCyberRadar`,
`ControlPlaneSecurityService`, payload/audit redaction in
`unifiedAgentAdapter`, Content-Security-Policy builder, frontend SRI for
self-hosted vendor libraries, and seven shell/Node boundary gates.

Discovery (Phase 1, 2026-05-15) recorded specific weaknesses:

1. The Modal web endpoints in `.agents/modal_app.py` authenticate by a
   single shared static `AGENT_API_TOKEN` carried in the JSON body and
   compared with plain `==` — no per-caller identity, no replay defense,
   no timing-safe comparison.
2. `AuditService` writes to `console.log` only — there is no
   tamper-evident persistent trail suitable for PDPL/SAMA/NCA review.
3. `unifiedAgentAdapter`'s redaction patterns are not sovereignty-aware:
   they do not detect Saudi National ID, Iqama, SA-IBAN, Saudi mobile,
   or commercial-registration numbers.
4. Validation is post-hoc — `validate_output` exists, `validate_input`
   does not. Prompt injection and KSA-PII can reach the model before any
   gate fires.
5. `ALLOW_EXTERNAL_AI` is a binary on/off flag; egress is not constrained
   per task profile, per tenant, or per residency requirement.
6. Trace correlation breaks at the Modal hop — `x-request-id` and
   `x-task-id` are set by `unifiedAgentAdapter` but Modal endpoints do
   not propagate them, so audit records cannot be linked across hops.

This ADR records the design of **Qal'a (قلعة — "Fortress")**, a layered
defense covering those gaps. It is **architecture only**. No runtime
code is introduced by this ADR. No agents are activated by it. No
external service is contacted. Implementation proceeds through later
PRs, each scoped to a single Qal'a layer.

## Decision

Qal'a is a **set of fail-closed, deterministic security primitives**
that sit at the boundaries already defined by ADR-0001 and ADR-0002. It
does not introduce a new runtime, a new public surface, or a new
service. Every Qal'a component is one of:

- A deterministic Python validator under `.agents/validators/`.
- A deterministic Node/TypeScript primitive under `src/security/`,
  with a hand-maintained `.js` companion tracked by
  `scripts/check-service-divergence.mjs`.
- A shell boundary gate under `scripts/commander/`.
- A documentary policy under `.agents/policies/`.
- Tests under `tests/`.
- ADR / design records under `docs/decisions/` and `docs/security/`.

Qal'a does not introduce new runtimes, deployments, public routes, or
always-on activation flags. It does not change ADR-0001's forbidden
path list.

## Layer Specification

The mission brief named nine defense layers. This ADR maps each layer
either to an existing surface (extended, not replaced) or to a new
Qal'a primitive. Layers are numbered Q1–Q9 to disambiguate from any
external numbering.

| # | Layer | Status | Surface |
|---|---|---|---|
| Q1 | Identity & authentication | EXTEND | `ControlPlaneSecurityService`; Modal-edge HMAC deferred to ADR-0004 |
| Q2 | Authorization & policy | EXTEND | `unifiedAgentAdapter.PolicyService`, `.agents/router/model_policy_engine` |
| Q3 | Input-side validation gate | NEW | `.agents/validators/qala_input_gate.py` (Phase 2 item 5) |
| Q4 | Output validation gate | EXTEND | `.agents/validators/bayyinah_validation_gate.py` (existing) |
| Q5 | Sovereign PII detection | NEW | `.agents/validators/qala_ksa_pii.py` + `src/security/qalaKsaPii.ts` (Phase 2 item 4) |
| Q6 | Trace & correlation | NEW | `.agents/validators/qala_trace.py` + `src/security/qalaTrace.ts` (Phase 2 item 2) |
| Q7 | Sealed audit sink | NEW | `.agents/validators/qala_audit_sink.py` + `src/security/qalaAuditSink.ts` (Phase 2 item 3) |
| Q8 | Egress residency gate | NEW | `scripts/commander/qala-egress-residency-gate.sh` + `.agents/policies/qala-egress-residency.md` (Phase 2 item 7) |
| Q9 | Threat detection / radar | EXTEND | `src/security/sovereignCyberRadar.ts` (existing) |

### Q1 — Identity & authentication

**Existing.** `ControlPlaneSecurityService` enforces Cloudflare Access
JWT + MFA claim + trusted issuer for the operator-static control plane.
The Modal-edge identity model (single shared body token, plain `==`
compare) is documented as the highest-leverage weakness in Phase 1
discovery.

**Qal'a extension.** Modal-edge HMAC replacement is *deferred* to
`ADR-0004` (Phase 2 item 6). This ADR explicitly does not authorize
the implementation. Modal endpoints, vLLM model weights, and the
shared `AGENT_API_TOKEN` rotation cadence remain as-is until ADR-0004
is accepted.

**Hot-surface classification.** Modal-edge auth is a hot surface per
`.agents/policies/execution-discipline-maximum.md` §5. Any change
must satisfy hot-surface discipline (no parallel implementation
tracks, re-check base branch before reopening work).

### Q2 — Authorization & policy

**Existing.** `unifiedAgentAdapter.DefaultPolicyService` enforces
`tenant_id == principal_tenant_id`, scope allowlist, and capability
allowlist with explicit reason codes (`CROSS_TENANT_ACCESS_DENIED`,
`UNAUTHORIZED_SCOPE`, `CAPABILITY_DENIED`).
`.agents/router/model_policy_engine.choose_route` maps `TaskProfile` to
`ModelRoute` deterministically and requires Bayyinah review for
critical/legal/coding routes.

**Qal'a extension.** None in Phase 2. Q2 is already fail-closed and
deterministic. Egress decisions move to Q8 (residency gate).

### Q3 — Input-side validation gate (NEW)

**Function.** Mirror of `bayyinah_validation_gate.validate_output` but
applied to the *prompt* before any model is invoked. Verdict contract is
identical (`APPROVE | REQUEST_CHANGES | BLOCKED`) so callers can branch
uniformly. Fail-closed: any uncertainty returns `BLOCKED`.

**Checks (Phase 2 minimum):**

- Prompt-injection phrase set (Arabic + English) — shared with
  `bayyinah_validation_gate`.
- KSA-PII detection via Q5 module.
- Unauthorized network execution patterns (`curl`, `wget`,
  `requests.post`, `fetch(`, `urllib.request`).
- Excessive size — input length limit consistent with adapter's
  `MAX_INPUT_LENGTH=8000`.
- Tenant identifier required when `TaskProfile.tenant_id` is set.

**Out of scope.** Semantic similarity / embedding-based injection
detection (would require external model calls — forbidden per
`network-boundary.md`).

### Q4 — Output validation gate

**Existing.** Covered by `bayyinah_validation_gate.validate_output`.
Q3 reuses its verdict types so the gate pair is symmetric.

### Q5 — Sovereign PII detection (NEW)

**Function.** Detect Saudi-specific identifiers in any text payload.
Distinct from generic secret detection (which lives in
`sovereignCyberRadar.SECRET_PATTERNS` and adapter `SENSITIVE_PATTERNS`).

**Identifier set (Phase 2 minimum):**

| Identifier | Format |
|---|---|
| Saudi National ID | 10 digits, leading digit `1` |
| Iqama | 10 digits, leading digit `2` |
| SA-IBAN | `SA` + 22 digits |
| Saudi mobile | `+9665` or `9665` or `05`, then 8 digits |
| Commercial registration (CR) | 10 digits, typically prefixed `10`/`20`/`30`/`40` — Phase 2 uses 10-digit + word-boundary discipline |

**Output contract.** Returns a tuple of `(category, masked_value,
match_span)` per hit. **Raw match values are never returned** — the
masked form preserves only first/last two characters with the middle
replaced by `…`. The audit emitter never logs raw values.

**Anti-collision.** National ID, Iqama, and CR all match 10-digit
shapes. Disambiguation is by **leading digit** plus explicit context
hint when supplied; otherwise the most specific category wins and the
result is labeled `KSA_ID_AMBIGUOUS_10DIGIT` for downstream handling.

### Q6 — Trace & correlation (NEW)

**Function.** A shared, dependency-free trace context that survives
adapter → router → validator → audit-sink → (future) Modal-edge HMAC.

**Schema.** `(trace_id, span_id, parent_span_id, tenant_id, phase,
started_at)`. IDs are UUIDv4. `phase` is an enum:
`input_validation | policy_check | model_call | output_validation |
egress_check | audit_emit | auth_check`.

**Transport.** Six headers: `x-qala-trace-id`, `x-qala-span-id`,
`x-qala-parent-span-id`, `x-qala-tenant-id`, `x-qala-phase`,
`x-qala-started-at`. The serializer must never emit `Authorization`,
`Bearer`, secrets, or raw PII into headers. `tenant_id` *is* permitted
in headers — it is not a secret and Qal'a requires it for cross-hop
correlation.

**Constraints.** No network calls. No persistent state. No background
workers. Pure functions; deterministic given inputs.

### Q7 — Sealed audit sink (NEW)

**Function.** Append-only, tamper-evident audit log adapter that
`AuditService` (TS) and `bayyinah_validation_gate` (Py) can both write
to. Lifts the chained-SHA-256 ledger pattern already present in
`sovereignCyberRadar.EvidenceLedger` and generalizes it.

**Properties.**

- Each record carries `(record_id, prev_hash, record_hash, trace_id,
  span_id, tenant_id, event, occurred_at, payload)`.
- `record_hash = sha256(serialize(record, prev_hash))`. Tampering with
  any prior record invalidates the chain.
- Writer is **append-only**. No `update`/`delete` API.
- Default sink is local JSONL under `artifacts/security/` (gitignored
  path). Remote persistence is **deferred** and requires operator
  approval via a successor ADR — no external destinations are wired
  in Phase 2.
- Payload is sanitized through Q5 (KSA-PII) and the existing audit
  redaction set before serialization. Raw secrets and raw PII never
  reach the sink.
- Genesis hash is the literal `"GENESIS"` (matching the existing
  cyber-radar ledger pattern for migration continuity).

**Non-goal.** Cryptographic signing of the chain head, time-stamping
authority anchoring, blockchain anchoring, IPFS publication — all
explicitly deferred. The chain proves *internal* tamper-evidence, not
external attestation.

### Q8 — Egress residency gate (NEW)

**Function.** Source-time and CI-time check that no Qal'a-touched code
issues requests to destinations outside the approved residency set.
Fail-closed: an unknown destination blocks merge.

**Approved destinations (Phase 2 minimum, allowlist):**

| Destination | Purpose | Repository surface |
|---|---|---|
| `*.modal.run` | Sovereign coding agents (Mihwar / Bayyinah) | `.agents/modal_app.py`, `.agents/pr_review.py`, `.agents/providers/modal_provider.py` |
| `api.github.com` | PR review comments | `.agents/pr_review.py` |
| `huggingface.co` | Model weight pull (Modal runtime only, never client) | `.agents/modal_app.py` (Modal-side) |

Any other host found in repository code requires a successor ADR. The
gate scans `.agents/`, `src/`, and `scripts/` for `urllib.request`,
`requests.post`, `fetch(`, `XMLHttpRequest`, and bare URLs, then
verifies each host against the allowlist.

**Out of scope.** Runtime DNS firewalling, Cloudflare Worker egress
rules, eBPF socket interception — all deferred to operator-managed
infrastructure outside this repository.

### Q9 — Threat detection / radar

**Existing.** `sovereignCyberRadar` covers URL reputation, scam text,
secret leak, prompt injection, command abuse, dependency confusion,
simulation marker. Score → verdict (`SAFE | WATCH | SUSPICIOUS |
BLOCKED`) with chained-hash evidence ledger.

**Qal'a extension.** None in Phase 2. Q9 already supplies the chained
ledger pattern; Q7 generalizes it.

## Explicit non-goals (Phase 2 constraints)

Listed per the operator's strict Phase 2 ordering. None of the
following will be introduced by Qal'a code in this repository.
Future scope must be admitted via a successor ADR.

- **No XMPP** integration or transport.
- **No OpenFHE** or other homomorphic-encryption runtime.
- **No DID / IPFS** identifier or storage layer.
- **No SPADE** agent framework.
- **No AIS** (artificial immune system) runtime.
- **No autonomous swarm activation**; no `autoStart`.
- **No production endpoint calls** from repository-resident code.
- **No secrets printed** to logs, audit, or PR comments.
- **No public ingress** added (operator-static `public/{control,trust,
  index.html}` boundary preserved per ADR-0002).
- **No background workers**, schedulers, or always-on processes.
- **No remote audit persistence** without a successor ADR.
- **No Modal-edge HMAC implementation** until ADR-0004 is accepted.

## Sequencing & dependencies

Phase 2 PRs land in this order. Each PR must pass the
existing boundary gates before merge.

1. **ADR-0003** (this file). Architecture only.
2. **Q6 trace module.** Foundational; pure functions; no external state.
3. **Q7 sealed audit sink.** Consumes Q6 trace context for record IDs.
4. **Q5 KSA-PII detector.** Consumes Q7 for audit emission of detection events.
5. **Q3 input-side validation gate.** Consumes Q5 (PII), Q6 (trace), Q7 (audit).
6. **ADR-0004** for Modal-edge HMAC. Architecture only; implementation deferred.
7. **Q8 egress residency gate.** Shell + docs. Validates the rest of the layer.

PRs are stacked logically (later PRs import earlier modules) but each
PR is independently reviewable and revertable.

## Verification (per PR)

A Qal'a PR is considered ready for review when:

- `bash scripts/commander/p0-security-test-gate.sh .` passes.
- `bash scripts/commander/modal-boundary-gate.sh .` passes.
- `bash scripts/commander/adr-0001-boundary-gate.sh .` passes.
- `bash scripts/commander/agent-presence-gate.sh .` passes (or
  warns only on `SECRET_MISSING`, which is the expected local state).
- `python3 -m unittest discover -s tests` passes.
- `npm run check` passes (service-divergence + unit + ADR-0001 +
  cdn-sri).
- New tests for the Qal'a layer touched by the PR pass.
- No new entry under `public/` outside the ADR-0002 allowlist.
- No `*.modal.run` URL or Modal SDK import enters a client surface.
- No `autoStart` flag anywhere.

## Rollback notes

Each Qal'a layer is independent. To roll back a layer:

- Q6 / Q7 / Q5 / Q3: delete the Python module under
  `.agents/validators/`, the TypeScript module under `src/security/`,
  the `.js` companion, and the test file. No callers depend on
  Qal'a primitives in this Phase, so removal is local.
- Q8: delete the shell gate and the policy document; no other
  surface imports it.
- ADR-0003 itself: supersede by a later ADR — do not delete (ADRs
  are append-only by convention).

## Consequences

- Phase 1 discovery findings are now bound to a documented design and
  a fixed sequence.
- Any future PR claiming "Qal'a" surface must cite this ADR and the
  specific layer (Q1–Q9) it touches.
- Modal-edge auth weakness remains as-is until ADR-0004 is accepted.
  This is a known, deliberately-deferred gap.
- Remote audit persistence remains absent. Qal'a's chained-hash log
  proves only that local records have not been tampered with after
  the fact — not that they were emitted at the claimed time by a
  trusted writer. External attestation requires a successor ADR.
- Qal'a does not change the repository boundary in ADR-0001 or the
  static-artifact boundary in ADR-0002.

## Evidence label

This ADR is `VERIFIED` against the Phase 1 discovery audit (2026-05-15)
and the existing source tree. Runtime behavior of Qal'a components is
`UNVERIFIED` until each component's PR adds tests and passes the gate
suite listed under "Verification (per PR)".
