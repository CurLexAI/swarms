# GitHub Webhook Runbook — SR.BSM / LexPrim

## Boundary

`CurLexAI/swarms` is not the public application runtime. Do not add public product routes to this repository.

The GitHub webhook receiver must live in the application runtime that owns the public URL, for example:

```text
https://sr-bsm.onrender.com/api/webhooks/github
https://www.lexprim.com/api/webhooks/github
```

Do not use a GitHub repository page as the payload URL.

```text
https://github.com/CurLexAI/swarms
```

That URL returns a GitHub HTML response and will produce `403 Forbidden` for webhook POST deliveries.

## GitHub settings

```text
Payload URL: https://sr-bsm.onrender.com/api/webhooks/github
Content type: application/json
Secret: same value as GITHUB_WEBHOOK_SECRET in the application runtime
SSL verification: enabled
Events: ping, push, pull_request, issues, workflow_run
```

## Receiver requirements

The application receiver must:

1. Preserve the raw request body.
2. Verify `X-Hub-Signature-256` using HMAC-SHA256 and `GITHUB_WEBHOOK_SECRET`.
3. Reject missing or invalid signatures with `401`.
4. Return `200` for `ping` after signature verification.
5. Return `202` for accepted asynchronous events.
6. Log only delivery id, event name, repository full name, and sanitized status.
7. Never log webhook secrets, authorization headers, or full payloads that could contain private metadata.

## Expected diagnostics

| Response | Meaning | Action |
|---|---|---|
| `403 Forbidden · GitHub` | Payload URL still points to `github.com/...` | Edit the webhook URL and redeliver a new ping. |
| `404` from Render/SR.BSM | Host is correct but route is missing | Add `/api/webhooks/github` in the application repo. |
| `401` from Render/SR.BSM | Route exists but signature or secret mismatch | Compare GitHub webhook secret with runtime `GITHUB_WEBHOOK_SECRET`. |
| `200` for `ping` | Receiver wiring is valid | Test selected real events. |

## Minimal Node receiver shape for the application repo

```ts
import crypto from "node:crypto";

function verifyGitHubSignature(rawBody: Buffer, signature: string | undefined, secret: string): boolean {
  if (!signature?.startsWith("sha256=")) return false;
  const expected = "sha256=" + crypto.createHmac("sha256", secret).update(rawBody).digest("hex");
  const a = Buffer.from(signature, "utf8");
  const b = Buffer.from(expected, "utf8");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

Keep this implementation in SR.BSM/LexPrim, not inside `CurLexAI/swarms`.
