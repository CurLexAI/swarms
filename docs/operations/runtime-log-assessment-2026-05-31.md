# Runtime Log Assessment — GitHub Webhook 401 — 2026-05-31

VERIFIED:
- The supplied runtime log slice for 2026-05-31T20:55:31Z through 2026-05-31T20:55:39Z contains repeated `POST /api/webhooks/github` requests from `GitHub-Hookshot/c97f169` with HTTP `401` responses.
- The supplied log slice contains repeated runtime errors with message `Cannot verify GitHub webhook signature: missing GITHUB_WEBHOOK_SECRET security configuration`.
- The supplied log slice contains repeated warnings with message `Rejecting GitHub webhook request: signature validation failed`.
- The supplied log slice contains a later level-50 `Polling error` with `error: fetch failed` at 2026-05-31T20:59:51.864625628Z.

CHANGED:
- Added this evidence-backed assessment for the 2026-05-31 webhook failure log slice.
- Updated the GitHub webhook runbook to distinguish a missing runtime secret from a generic signature mismatch.
- Repaired `package.json` JSON syntax so local npm-based validation commands can be parsed and executed.

VALIDATION:
- The webhook receiver is rejecting unsigned/unverifiable traffic because the runtime secret is absent; this is fail-closed behavior and must not be bypassed.
- Repository-local remediation is limited to runbook and validation-gate correctness because live runtime secret configuration must happen in the deployment secret store.

RISKS:
- UNVERIFIED_RUNTIME: The live runtime was not accessed, restarted, or reconfigured from this repository session.
- SECRET_MISSING: `GITHUB_WEBHOOK_SECRET` must be configured in the application runtime secret store and matched in GitHub webhook settings before GitHub deliveries can verify successfully.
- POLLING_ERROR_UNRESOLVED: The later `fetch failed` polling error is a separate runtime connectivity symptom until endpoint, DNS, TLS, and retry telemetry are inspected.

DECISION:
- Status = CHANGED_BUT_RUNTIME_UNVERIFIED.
- Do not disable signature checks, do not add a default webhook secret, and do not commit any real secret value.

NEXT ACTION:
1. In the runtime secret store, set `GITHUB_WEBHOOK_SECRET` to a newly generated high-entropy value.
2. In GitHub webhook settings, set the webhook secret to the exact same value.
3. Restart or redeploy the runtime so the process reads the new secret.
4. Redeliver a GitHub `ping` event and verify a `200` response with no missing-secret log.
5. Investigate the 2026-05-31T20:59:51Z `Polling error` separately with non-secret endpoint class, DNS/TLS/socket timeout, and retry metadata.
