# LexPrim Chat Gateway — Integration Spec

> **Purpose:** Authoritative contract for the chat gateway that a separate
> LexPrim/Qarar product repo will implement to give the founder's control
> panel and other authorized clients a direct conversational surface to the
> sovereign agents (Mihwar, Bayyinah, Free Birds, and any future swarm
> defined in `agents/registry.yaml`).
>
> **Scope of this document:** specification only. No runtime, route, or UI
> code lives in `CurLexAI/swarms` — that would breach ADR-0001. This file
> exists here so the agent operations layer publishes one canonical contract
> that the product repo must conform to.

---

## 1. Topology (non-negotiable)

```text
Client (browser / iPhone / founder control panel)
    │  HTTPS (TLS 1.3)
    ▼
Cloudflare edge   (WAF, DNS, mTLS terminator if used)
    │  HTTPS, mTLS optional
    ▼
Render origin     (public gateway service in the product repo —
                   NOT in swarms)
    │  HMAC bearer (AGENT_API_TOKEN)
    ▼
Modal runtime     (MIHWAR_ENDPOINT, BAYYINAH_ENDPOINT)
```

**Hard rules:**
1. The client must **never** call `*.modal.run` directly. The
   `modal-boundary-gate.sh` in `swarms` enforces this and any product PR
   that violates it must be rejected at review.
2. The bearer token (`AGENT_API_TOKEN`) lives only on the Render origin
   server. Browsers and mobile clients must never see it.
3. The product repo is responsible for its own session auth between
   client and Render. The Render origin then attaches `Authorization:
   Bearer ${AGENT_API_TOKEN}` when calling Modal.
4. Both directions must be HTTPS. No mixed content, no fallback to HTTP.

---

## 2. Authentication

### 2.1 Client → Render

The product repo chooses the session mechanism (LexPrim SSO, OIDC, signed
cookie, etc.). Whatever is chosen must:

- Be replay-resistant (nonce, short-lived JWT, or rotating cookie).
- Carry the operator identity that will appear in the audit trail.
- Be revocable from the founder panel without redeploy.

### 2.2 Render → Modal

Single shared secret, HMAC bearer:

```http
Authorization: Bearer <AGENT_API_TOKEN>
Content-Type: application/json
```

- Token rotation cadence: 90 days (per `docs/secrets-policy.md`).
- Rotation procedure: ADR-0004 (`docs/decisions/ADR-0004-qala-modal-edge-hmac-auth.md`).
- The Render origin must reject any request from the client that attempts
  to set or override `Authorization` — the header is injected server-side.

---

## 3. HTTP contract

### 3.1 Base path

```
POST  /v1/chat/completions          # single-turn or multi-turn chat
POST  /v1/chat/stream               # server-sent events (SSE) for streaming
GET   /v1/agents                    # list configured agents and swarms
GET   /v1/agents/{id}               # capability descriptor for one agent
POST  /v1/agents/{id}/invoke        # direct single-agent invocation
GET   /v1/health                    # liveness; never reveals secrets
```

### 3.2 `POST /v1/chat/completions`

Request body:

```json
{
  "agent_id": "free-birds",
  "subcommand": "review",
  "messages": [
    {"role": "system", "content": "...optional client-side prompt..."},
    {"role": "user",   "content": "راجعوا هذا الـ PR رقم 219"}
  ],
  "attachments": [
    {"type": "diff",       "content": "...unified diff..."},
    {"type": "file",       "path": "src/auth.ts", "content": "..."},
    {"type": "url",        "value": "https://github.com/...pr/219"}
  ],
  "focus":   ["security_review", "merge_safety"],
  "stream":  false,
  "metadata": {
    "session_id": "...",
    "operator":   "founder@lexprim",
    "client":     "control-panel/v1.4.2"
  }
}
```

Response body:

```json
{
  "id": "chat_01J...",
  "agent_id": "free-birds",
  "subcommand": "review",
  "verdict": "REQUEST_CHANGES",
  "findings": [
    {"bird": "shaheen", "severity": "HIGH",   "file": "src/auth.ts:42",
     "message": "Token compared with == instead of timingSafeEqual"},
    {"bird": "harrier", "severity": "MEDIUM", "file": "public/index.html:7",
     "message": "Embedded *.modal.run URL — modal-boundary violation"}
  ],
  "messages": [
    {"role": "assistant", "content": "...consolidated review text..."}
  ],
  "usage": {
    "input_tokens":  4231,
    "output_tokens": 1180,
    "model":         "Qwen/Qwen2.5-Coder-32B-Instruct",
    "endpoint":      "BAYYINAH_ENDPOINT"
  },
  "audit": {
    "request_id": "req_01J...",
    "ts":         "2026-05-23T18:21:44Z",
    "operator":   "founder@lexprim"
  }
}
```

### 3.3 `POST /v1/chat/stream`

Same request body. Response is SSE:

```
event: token
data: {"delta": "..."}

event: finding
data: {"bird": "falcon", "severity": "CRITICAL", ...}

event: done
data: {"verdict": "BLOCK", "usage": {...}, "audit": {...}}
```

### 3.4 `GET /v1/agents`

Returns the publishable subset of `agents/registry.yaml`. **Filter out**
any `endpoint_env`, `token_env`, or `provider.kind` field — the client
must never see the underlying Modal binding.

```json
{
  "agents": [
    {"id": "mihwar",   "name": "Mihwar — المحور",   "role": "architect_generator"},
    {"id": "bayyinah", "name": "Bayyinah — البيّنة", "role": "validator_reviewer"},
    {"id": "falcon",   "name": "Falcon — الصقر",    "role": "code_review"},
    {"id": "owl",      "name": "Owl — البومة",       "role": "architecture_design"}
  ],
  "swarms": [
    {"id": "coding-swarm", "name": "سرب البرمجة — Coding Swarm", "members": ["mihwar","bayyinah"]},
    {"id": "free-birds",   "name": "Free Birds — الطيور الحرة",   "members": [...]}
  ]
}
```

---

## 4. Agent selection

The `agent_id` field accepts:

- A single canonical agent from `.agents/config/agents.yaml`: `mihwar`,
  `bayyinah`.
- Any registered entry from `agents/registry.yaml`: e.g. `qarar-router`,
  `falcon`, `owl`, `phoenix`.
- A swarm id: `coding-swarm`, `routing-swarm`, `free-birds`.

`subcommand` is interpreted per-target:

| Target            | Valid subcommands              | Default   |
|-------------------|--------------------------------|-----------|
| Single agent      | (none)                         | —         |
| `coding-swarm`    | `review`, `design`, `full`     | `full`    |
| `routing-swarm`   | (none — runs the full pipeline)| —         |
| `free-birds`      | `review`, `design`, `full`     | `review`  |

`focus` narrows the work scope; for swarms it can restrict to a subset of
bird ids; for single agents it is passed through as a capability hint.

---

## 5. Error model

All errors use the same envelope:

```json
{
  "error": {
    "code":    "UNVERIFIED" | "SECRET_MISSING" | "CONFIG_NOT_FOUND" |
               "AUTH_MISSING" | "MODEL_TIMEOUT" | "POLICY_BLOCKED" |
               "VALIDATION_FAILED" | "INTERNAL",
    "message": "...short human-readable...",
    "request_id": "req_01J..."
  }
}
```

`POLICY_BLOCKED` is reserved for cases where the Render gateway rejects
the request because it tries to bypass a swarms policy (e.g. requesting a
Modal URL, requesting a secret value). The Render origin must log these
to the audit sink.

`UNVERIFIED` and `SECRET_MISSING` mirror the swarms status labels and must
not be silently coerced into success.

---

## 6. Streaming, cancellation, timeouts

- Default request timeout: 180 s (matches Modal endpoint timeout).
- SSE streams must emit a heartbeat `event: ping` every 15 s.
- Client cancellation: closing the SSE connection MUST abort the
  upstream Modal request (Render origin propagates cancellation).
- A single client session may not hold more than 3 concurrent streams.

---

## 7. Audit

Every request and every finding must be persisted to the audit sink that
mirrors `.agents/validators/qala_audit_sink.py`. Minimum fields:

- `request_id`
- `ts` (UTC, ISO-8601)
- `operator`
- `agent_id`, `subcommand`, `focus`
- `model`, `endpoint` (env name, NOT URL)
- `verdict`
- `input_token_count`, `output_token_count`
- `severity_summary`: `{critical, high, medium, low, info}` counts
- `policy_blocks`: list (or empty)

Audit retention follows `docs/trust/data-retention-policy.md`.

---

## 8. PII and KSA residency

The gateway must call `qala_ksa_pii.py`-equivalent redaction on any
request/response chunk that contains:

- Saudi national IDs (10-digit, validated)
- IBANs
- Phone numbers with `+9665` prefix
- Email addresses where the local part matches a personal pattern

Redaction happens **before** persistence to audit, never after. The
underlying `qala_*` validators live in `swarms` and must not be
re-implemented in the product repo — they should be consumed as a Python
package or via the validator HTTP wrapper described in Section 9.

---

## 9. Validator HTTP wrapper (planned)

`swarms` will expose the Qala validators (`qala_input_gate`,
`qala_ksa_pii`, `qala_audit_sink`, `qala_trace`, plus
`bayyinah_validation_gate`) as a small internal HTTP service running
alongside the Modal endpoints. The product gateway:

1. Posts the inbound payload to `/qala/input` for PII/policy validation.
2. On `200 OK`, dispatches to Modal.
3. Posts the outbound payload to `/qala/output` for redaction and audit
   sink writing.
4. Returns the redacted output to the client.

The validator wrapper is **not yet implemented**. Tracking issue to be
filed before any production traffic.

---

## 10. Boundary checklist (for the product repo's PR review)

A PR that integrates this gateway in the product repo must satisfy:

- [ ] No `*.modal.run` URL appears in any file under `client/`, `web/`,
      `public/`, `app/`, `mobile/`, or marketing pages.
- [ ] `AGENTS.md`-equivalent or `CLAUDE.md`-equivalent file references
      this spec by URL.
- [ ] The bearer token is read only from a server-side secret manager.
- [ ] The list of agents shown in the UI is built from `GET /v1/agents`,
      not hard-coded.
- [ ] All requests carry an `operator` field and are persisted to audit.
- [ ] Streaming closes cleanly on client navigation away.
- [ ] Error envelope is rendered as a user-facing message, never as
      `console.log`.
- [ ] The integration test suite includes a `POLICY_BLOCKED` case and a
      `SECRET_MISSING` case.

---

## 11. Versioning

This spec is `v1`. Breaking changes require a new path prefix
(`/v2/chat/...`) and a deprecation window of 90 days for `v1`. Additive
changes (new optional fields, new agent ids, new swarms) are
backwards-compatible and do not bump the version.

---

## 12. Cross-references

- `docs/decisions/ADR-0001-swarms-boundary.md` — why the gateway lives
  outside swarms.
- `docs/decisions/ADR-0004-qala-modal-edge-hmac-auth.md` — HMAC auth
  details for the Render → Modal hop.
- `docs/decisions/ADR-0005-public-llm-gateway.md` — high-level gateway
  decision record.
- `docs/secrets-policy.md` — required secrets and rotation cadence.
- `agents/registry.yaml` — source of truth for selectable `agent_id`
  values.
- `.agents/config/agents.yaml` — canonical agent profiles.
- `.agents/mcp/server.py` — reference implementation for the same
  invocation surface over MCP (mihwar_generate, bayyinah_review,
  free_birds_review, free_birds_design).
