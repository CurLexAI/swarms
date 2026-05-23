# Policy: Qal'a Egress Residency (Q8)

## Purpose

Block unapproved network destinations from entering repository-resident
source code. Defends data residency by forbidding egress to hosts
outside the documented sovereign allowlist. Source-time enforcement
only — this policy is not a runtime firewall (that responsibility
stays with the operator's Cloudflare / Modal infrastructure).

This policy is mandatory and cannot be downgraded to an optional
skill. See `docs/decisions/ADR-0003-qala-security-architecture.md`
§Q8.

---

## Allowlist (Phase 2 minimum)

| Host pattern | Purpose | Surface authorized to call |
|---|---|---|
| `*.modal.run` | Sovereign coding agents (Mihwar / Bayyinah) | `.agents/modal_app.py`, `.agents/pr_review.py`, `.agents/providers/modal_provider.py` |
| `api.github.com` | PR review comments, user info | `.agents/pr_review.py`, `.agents/mcp/cloudflare-mcp/src/github-handler.ts` |
| `github.com` | GitHub OAuth authorization and token exchange | `.agents/mcp/cloudflare-mcp/src/github-handler.ts` |
| `huggingface.co` | Model weight pull (Modal runtime only — never client) | `.agents/modal_app.py` |

Any other host appearing in scanned source files requires either:

1. A successor ADR adding it to the allowlist with a documented
   purpose and authorized-surface column, **or**
2. Replacement with a sovereign-allowed alternative.

---

## Scope

The gate scans:

- `.agents/` (Python operations layer)
- `src/` (Node / TypeScript adapters)
- `scripts/` (build/check scripts)

It does NOT scan:

- `docs/` — documentation may reference example URLs without making
  network calls.
- `tests/` — test fixtures may reference any URL because test code
  does not run against production.
- `node_modules/`, `.git/`, build artifacts.

---

## Detection patterns

The gate flags occurrences of any of:

- Bare host literals matching `https?://<host>`.
- `urllib.request` / `requests.post` / `requests.get` / `fetch(` /
  `XMLHttpRequest` callsites whose URL argument resolves to a
  literal host.
- Modal endpoint env-name references (`MIHWAR_ENDPOINT`,
  `BAYYINAH_ENDPOINT`, `MODAL_RELAY_UPSTREAM_URL`) — these are
  treated as `*.modal.run` callers.

Each unique host is checked against the allowlist. The first match
that violates the allowlist FAILs the gate.

---

## Fail-closed behavior

- An empty allowlist FAILs the gate (no scan = no decision).
- An unparseable host FAILs the gate.
- A scanner runtime failure FAILs the gate (exit ≥ 2 — never silent
  pass).
- A host that matches an allowlist *pattern* but appears in a
  surface outside the authorized list (per the table above) is
  reported as `EGRESS_SURFACE_VIOLATION` for human review — does
  not auto-pass.

---

## Allowed exemptions (none)

There are no documented exemptions in Phase 2. Future exemptions
require a successor ADR.

---

## Report fields

```text
EGRESS_HOSTS_SCANNED: <count> (or NONE)
ALLOWLISTED_HOSTS: <set>
UNAPPROVED_HOSTS: <set or NONE>
SURFACE_VIOLATIONS: <set or NONE>
ACTION: PASS | FAIL_UNAPPROVED_EGRESS | FAIL_SCANNER_ERROR
```

---

## Out of scope

- Runtime DNS firewalling, Cloudflare Worker egress rules, eBPF
  socket interception — deferred to operator-managed infrastructure
  outside this repository.
- Subdomain enumeration — `*.modal.run` is treated as a single
  allowlist entry; the operator is responsible for tenant-scoped
  Modal endpoint hygiene.
- IP-literal egress (e.g. `http://10.0.0.1`) — the gate flags any
  IP literal as unapproved regardless of address; static IP egress
  is forbidden without a successor ADR.
