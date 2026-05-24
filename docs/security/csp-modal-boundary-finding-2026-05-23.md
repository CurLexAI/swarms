# CSP → Modal Boundary Finding (2026-05-23)

| Field | Value |
|---|---|
| Severity | **HIGH** |
| Status | `OPEN` — tracked in `swarms`; fix lives in the frontend repo |
| ADR conflict | ADR-0001 (`docs/decisions/ADR-0001-swarms-boundary.md`) |
| Detected by | Pre-launch commander audit (`/codex-commander` + `/public-surface-auditor`) |
| Detected at | 2026-05-23 |
| Repository of record | `CurLexAI/swarms` (this repo) |
| Repository of fix | LexPrim frontend repo (separate) |

---

## What was observed

Probing the deployed public surface with `curl -I https://www.lexprim.com`
returned the following `Content-Security-Policy` header (line-wrapped for
readability; the underlying header is one line):

```
content-security-policy:
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com data:;
  img-src 'self' data:;
  connect-src 'self'
              https://*.modal.run
              https://api.openai.com
              https://api.anthropic.com
              https://api.perplexity.ai
              https://api.groq.com
```

The `connect-src` directive explicitly authorises browsers loading
`www.lexprim.com` to open `fetch` / `XHR` / `WebSocket` connections to:

- `https://*.modal.run`
- `https://api.openai.com`
- `https://api.anthropic.com`
- `https://api.perplexity.ai`
- `https://api.groq.com`

## Why this is a finding

The `*.modal.run` entry contradicts the boundary rule recorded in
`ADR-0001-swarms-boundary.md` and re-asserted in the
`modal-runtime-operator` skill:

> Modal is backend-only. Never expose Modal URLs to browser, iPhone,
> frontend, or any public client surface.

Allowing `connect-src https://*.modal.run` from a public-facing origin
permits any script running in the browser context (including any future
XSS vector through the `'unsafe-inline'` `script-src`) to call private
Modal endpoints directly. Even without an active XSS, the CSP itself is
an architectural signal that frontend code is calling Modal directly
rather than going through the Render origin gateway, which:

1. Bypasses the planned WAF / rate-limit / audit layer.
2. Makes Modal endpoint URLs effectively public (DNS-discoverable from
   network logs and browser devtools).
3. Couples the frontend release cadence to the Modal endpoint surface.

The `api.openai.com`, `api.anthropic.com`, `api.perplexity.ai`, and
`api.groq.com` entries indicate the same architectural pattern is
applied to several third-party model providers. Those entries imply
provider API keys are reachable from the browser context, which is a
separate **CRITICAL** key-exposure concern that should be triaged
alongside the Modal entry.

## Why this finding lives in `swarms` and not the frontend repo

`swarms` is the canonical record for the agent-runtime boundary (see
ADR-0001) and the home of the `modal-runtime-operator` and
`public-surface-auditor` skills that detected the violation. The fix
itself must land in the frontend repo. This file exists so:

- The audit trail in `swarms` does not lose the finding when the
  frontend repo is patched.
- The COMMANDER REPORT for the launch can reference a stable URL.
- A future re-audit can confirm the finding is `RESOLVED` once the
  CSP is tightened and re-probed.

## Required remediation (frontend repo)

1. Remove `https://*.modal.run` from the `connect-src` directive.
2. Remove the four third-party model-API entries (`openai`,
   `anthropic`, `perplexity`, `groq`) from `connect-src` unless the
   frontend genuinely needs to call them with anonymous keys (rare and
   risky).
3. Route all Modal traffic through the Render origin gateway. The
   browser should call `connect-src 'self'` (or a same-origin API
   subdomain), and the origin should proxy to Modal with a server-side
   bearer.
4. Remove `'unsafe-inline'` from `script-src` if at all possible, or
   pair it with a strict nonce/hash policy.
5. Re-run the public-surface check below and attach the new headers.

## Re-audit command

After the frontend CSP is tightened, run:

```bash
curl -sS -I https://www.lexprim.com | grep -i 'content-security-policy'
```

Expected: no `*.modal.run`, no third-party model-API hosts in
`connect-src`. Once verified, change `Status: OPEN` at the top of this
file to `Status: RESOLVED` with the new CSP value pasted below this line
and the re-audit date recorded.

## Related artifacts

- `docs/decisions/ADR-0001-swarms-boundary.md` — boundary record.
- `.agents/skills/modal-runtime-operator/SKILL.md` — backend-only rule.
- `.agents/skills/public-surface-auditor/SKILL.md` — audit playbook.
- `scripts/commander/modal-boundary-gate.sh` — the gate that protects
  this repo from the same drift; passes locally because no
  `*.modal.run` reference exists in `src/` or `public/` of `swarms`.
- `docs/launch-evidence/agent-launch.md` — launch readiness; cannot
  reach `READY` while this finding is `OPEN`.

## Tracking

Resolves the *recording* half of **B2** from the 2026-05-23 pre-launch
commander audit. The *fix* still requires a separate PR in the
frontend repository.
