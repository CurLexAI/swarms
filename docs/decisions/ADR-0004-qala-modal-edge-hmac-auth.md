# ADR-0004 — Modal-Edge HMAC Authentication (Q1)

- **Status:** Proposed (architecture only — implementation NOT authorized by this ADR)
- **Decision date:** 2026-05-15
- **Decision owner:** Repository operator
- **Supersedes:** none
- **Superseded by:** none
- **Relates to:** ADR-0001 (swarms boundary), ADR-0003 (Qal'a security architecture)
- **Hot-surface classification:** YES per `.agents/policies/execution-discipline-maximum.md` §5

## Context

Phase 1 discovery (2026-05-15) identified the Modal web endpoints in
`.agents/modal_app.py` as the highest-leverage authentication weakness
in the repository. The current model is:

- A single shared static token (now retired for Modal endpoint auth) projected into both
  `bayyinah_review_web` and `mihwar_generate_web` via the
  `agent-api-secret` Modal secret.
- The token is carried in the JSON request body under a `"token"` key
  rather than in an `Authorization` header.
- The comparison is `payload.get("token") == expected_token` — plain
  string equality, not `hmac.compare_digest`.
- There is no per-caller identity, no replay defense, no per-endpoint
  scope, no rate limit, and no nonce or timestamp.
- The same token grants Bayyinah review and Mihwar generation; one
  compromise grants both capabilities.

The token is the only authentication factor between GitHub Actions
runners (running `.agents/pr_review.py`) and the Modal-hosted sovereign
model runtime. A leaked token compromises the entire model runtime
authentication surface until the operator rotates `agent-api-secret`.

ADR-0003 §Q1 deferred the Modal-edge identity model to this ADR. This
ADR records the **proposed** replacement design and the gating
conditions that must be satisfied before any implementation may begin.
This ADR does **not** authorize implementation.

## Decision (proposed)

Replace the single-static-token model with a signed-request scheme
based on HMAC-SHA-256 and short-lived signing keys, scoped per
caller and per endpoint. The design is documented here so it can be
reviewed independently of the implementation work.

### Authentication envelope

Each request to a Modal endpoint carries:

| Header | Value |
|---|---|
| `x-qala-key-id` | Caller identifier (e.g. `gha-pr-review` for the GitHub Actions runner). |
| `x-qala-timestamp` | Unix epoch seconds at signing time. |
| `x-qala-nonce` | Random 16-byte hex string, unique per request. |
| `x-qala-signature` | `HMAC-SHA-256(secret, canonical_request)` in hex. |
| `x-qala-endpoint` | Endpoint name (`bayyinah-review` or `mihwar-generate`). |
| `x-qala-trace-id` / `x-qala-span-id` / `x-qala-tenant-id` / etc. | Q6 trace headers (already designed). |

The body is JSON without an embedded `"token"` field. The token is
removed from the body entirely.

### Canonical request

```
canonical_request = key_id || "\n" ||
                    endpoint || "\n" ||
                    timestamp || "\n" ||
                    nonce || "\n" ||
                    trace_id || "\n" ||
                    sha256_hex(body)
```

Field separator is a single `\n`. `sha256_hex(body)` is the SHA-256
hex digest of the raw request body bytes (deterministic regardless of
JSON key order, because the client must sign the bytes it actually
sends).

### Verification (server side)

The Modal endpoint:

1. Rejects the request if `endpoint` does not match the route the
   request hit (route-binding check; defends against header confusion).
2. Rejects if `|now - timestamp| > 300s` (replay window).
3. Rejects if `nonce` has been seen within the replay window (nonce
   cache; can be a simple in-memory ring per Modal container).
4. Looks up the per-`key_id` secret from a Modal secret bundle
   (per-key naming: `agent-key-<key_id>`).
5. Recomputes the canonical request, recomputes the HMAC, and
   compares with `hmac.compare_digest` — never `==`.
6. On any mismatch, returns `{"error": "unauthorized", "verdict":
   "BLOCKED"}` and emits a `auth_check_blocked` record to the Q7
   sealed audit sink with `key_id`, `endpoint`, and the reason code
   (never the signature, never the secret).

### Per-endpoint scope

Each `key_id` is mapped to an allowed-endpoint set in a Modal config
bundle. `gha-pr-review` is allowed `bayyinah-review` and
`mihwar-generate`; future caller identities (e.g. a future operator
console) get their own narrower allowlists.

### Key rotation

- Each `key_id` carries a `key_version`. Modal config bundles support
  a primary and a secondary version per key for zero-downtime
  rotation.
- Rotation cadence: 30 days for `gha-pr-review`. (Tighter than the
  current 90-day cadence recorded in `docs/secrets-policy.md` because
  the per-key secrets are higher-frequency than the shared token they
  replace.)
- `docs/secrets-policy.md` will be updated when this ADR is accepted
  to reflect the new key naming and rotation policy.

## Sequencing (proposed; not authorized)

If and only if this ADR is accepted, implementation proceeds in this
order:

1. **Update `docs/secrets-policy.md`** with the new key-naming
   convention and rotation cadence. No implementation, no secret
   rotation.
2. **Add Python signing helper** under `.agents/validators/qala_modal_hmac.py`
   — pure function, no network, with cross-language equivalence tests
   against a TypeScript signing helper.
3. **Add TypeScript signing helper** under `src/security/qalaModalHmac.ts`
   (and `.js` companion) for any future Node-side caller.
4. **Extend `.agents/pr_review.py`** to sign outbound requests using
   the helper. Behind a `QALA_MODAL_AUTH_VERSION=hmac` env flag so the
   existing body-token path remains as a fallback during rollout.
5. **Extend `.agents/modal_app.py`** web endpoints to accept both the
   legacy body-token AND the HMAC envelope. Verify HMAC first; fall
   back to legacy token only when `QALA_MODAL_LEGACY_TOKEN_ENABLED=true`.
6. **Operator runbook**: rotate `agent-api-secret`, mint per-`key_id`
   secrets, set `QALA_MODAL_AUTH_VERSION=hmac` in the GitHub Actions
   environment, observe one cycle of green agent reviews, then disable
   the legacy path.
7. **Remove legacy body-token code path** in a follow-up PR after the
   operator confirms zero legacy-path traffic for a documented
   observation window.

Each step lands as its own PR with the standard report block
(files / threat boundary / validation / rollback / VERIFIED labels).
Steps 4–7 touch hot-surface auth code and must obey
`.agents/policies/execution-discipline-maximum.md` §5.

## Hot-surface conditions

Per §5 of the execution-discipline policy, this work is hot-surface
and must satisfy these conditions before any step begins:

- No parallel implementation track on Modal-edge auth in another PR
  or branch.
- Base branch (`main`) re-checked at the start of every reopened
  step.
- `scripts/commander/modal-boundary-gate.sh` PASSes throughout.
- No `*.modal.run` URL or token value enters any audit log, PR
  comment, or test fixture (per `.agents/policies/secrets-boundary.md`).
- Bayyinah review of every signing-related diff before merge.

## Gating conditions before implementation

This ADR is *Proposed*. Implementation does not begin until **all** of:

1. Operator explicit go-ahead, in writing, referencing this ADR.
2. ADR status flipped from *Proposed* to *Accepted* via a separate PR.
3. The seven sequencing steps above are scheduled as separate PRs
   with named owners.
4. The legacy path remains as a fallback during the entire rollout
   window; no PR may delete it before step 7.

## Explicit non-goals

- **No mTLS** with client certificates — operator infrastructure does
  not yet provision certs for Actions runners; HMAC + Modal-managed
  secrets is the simplest sovereign-friendly upgrade that does not
  require new infrastructure.
- **No JWT** — JWT introduces clock-skew, alg-confusion, and library
  selection risks that the HMAC envelope avoids.
- **No external identity provider** for the Actions runner — keeping
  the trust root inside Modal's secret bundle preserves the boundary.
- **No new public surface** — HMAC verification stays inside the
  existing Modal web endpoints.
- **No removal of the legacy path in the same PR that introduces
  HMAC** — overlap prevents auth outages during rollout.

## Threat boundary affected

Q1 Modal-edge identity & authentication. After acceptance and full
rollout, the following Phase 1 weaknesses are addressed:

- Per-caller identity (key_id) replaces the shared principal.
- `hmac.compare_digest` replaces plain `==`.
- Timestamp + nonce defend against replay.
- Per-endpoint scope reduces blast radius of a single key compromise.
- Token leaves the request body — body bytes are signed, not
  authenticated by inclusion.

## Validation criteria (for the eventual implementation PRs)

A signing-related PR is ready for review when:

- Cross-language signing equivalence test passes (TS and Python
  produce identical signatures for identical canonical requests).
- Replay test passes (a captured request fails on second submission).
- Clock-skew test passes (a request older than 300 s is rejected).
- Endpoint-confusion test passes (a request signed for
  `bayyinah-review` is rejected by `mihwar-generate`).
- Legacy fallback test passes (with `QALA_MODAL_LEGACY_TOKEN_ENABLED=true`
  and the HMAC envelope absent, the body-token path still authenticates).
- All Phase 2 gates continue to PASS.

## Rollback notes

- Revert the implementation PR(s) in reverse order (7 → 1).
- Re-enable the legacy body-token path by setting
  `QALA_MODAL_LEGACY_TOKEN_ENABLED=true` and unsetting
  `QALA_MODAL_AUTH_VERSION`.
- This ADR may be superseded by a later ADR if the design changes; do
  not delete it (ADRs are append-only by convention).

## Evidence

This ADR is `VERIFIED` against the Phase 1 discovery audit
(2026-05-15) and the proposed-but-not-yet-implemented design. Runtime
behavior of the HMAC scheme is `UNVERIFIED` and will remain so until
the implementation steps above land with their own tests.

## Decision (this ADR)

**Architecture is recorded. Implementation is NOT authorized by this
ADR.** A successor PR that flips `Status` from *Proposed* to
*Accepted*, plus written operator approval, is required before any
implementation work begins.
