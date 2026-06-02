# Qarar/Bayyinah Launch Governance

## Status

- **Launch verdict:** HOLD
- **Production principle:** verification before activation.
- **No-auto-deploy rule:** production Modal deployment is allowed only through an explicit manual `workflow_dispatch` action, a matching confirmation phrase, and the protected `production` environment approval. Push, pull request, and schedule events must never deploy Modal runtime.

## Data Classification Rules

| Class | Examples | Handling Rule | AI/Agent Route |
|---|---|---|---|
| Public | Published docs, public repository metadata | May be used in normal validation and reports. | Any approved non-mutating local route. |
| Internal | Non-secret runbooks, non-sensitive source code, validation summaries | Keep within approved repository and CI surfaces. | Local/offline agent route preferred; Modal only after approval. |
| Confidential | Private diffs, operational evidence, topology details | Do not expose to browser/client surfaces or external AI APIs. | Bayyinah/Mihwar private runtime only after endpoint smoke is verified. |
| Restricted | Secrets, bearer tokens, private endpoint URLs, regulated or sovereign data | Never print, commit, or send outside the sovereign path. | Sovereign-only route after classification, auth, audit, and operator approval. |
| Unclassified | Any input without a class label | Fail closed until classified by owner/operator. | Blocked. |

## Owner Approvals

| Gate | Required Approval | Evidence Required Before Approval |
|---|---|---|
| Governance | Platform owner | This file, launch scope, rollback path, incident path. |
| Secrets | Security owner | Secret names manifest only; no values in logs or repository. |
| Local gates | Platform owner | Passing command log or explicit blocker classification. |
| Modal deploy | Production approver | Manual workflow dispatch, protected `production` approval, required Modal secrets present. |
| Endpoint smoke | Runtime owner | HTTP 200 authenticated smoke, invalid-token failure, redacted logs. |
| Bayyinah PR gate | Security owner | Blocking behavior for absent evidence, missing attribution, low confidence, blocked verdict, and restricted-data egress. |
| Control boundary | Control-plane owner | Allow/deny/classification/sovereign-route decisions in audit log. |
| Device pilot | Operations owner | Allowlisted device, kill switch, manual operator, non-destructive scope. |
| Limited live | Incident commander + platform owner | Monitoring, rate limits, rollback, audit export, error budget. |
| Full live | Executive owner | All prior gates verified; no CRITICAL/HIGH blockers remain. |

## Rollback Plan

1. Stop new live traffic by setting the launch state to `HOLD` and disabling limited-live routing.
2. Disable runtime invocation by removing or revoking endpoint secrets in the approved secret store.
3. Re-run local gates and endpoint smoke after rollback to confirm the runtime is no longer used.
4. Preserve audit logs and launch evidence for incident review.
5. Re-enable only through the same manual launch ladder after root-cause closure.

## Kill Switch

- Primary kill switch: remove/revoke `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, `BAYYINAH_API_TOKEN`, and `MIHWAR_API_TOKEN` from the active runtime secret store.
- Secondary kill switch: disable `ALLOW_LIMITED_LIVE` or equivalent launch flag in the deployment environment.
- Emergency CI kill switch: disable the Modal runtime workflows in GitHub Actions until investigation completes.
- The kill switch must not require code changes, branch merges, or production redeploys.

## Launch Scope

In scope:

- Repository governance evidence.
- Required secret-name manifest without values.
- Local validation gates.
- Manual Modal deployment instructions only.
- Smoke-test evidence placeholders and fail-closed readiness verdict.

Out of scope until explicit approval:

- Production deployment.
- Live endpoint invocation.
- Destructive device commands.
- Full-live activation.
- External AI API calls.
- Merge or production mutation.

## Incident Path

1. Operator declares incident severity and freezes live activation.
2. Security owner reviews audit evidence and secret exposure risk.
3. Platform owner runs rollback plan and records command outputs with sensitive values redacted.
4. Incident commander decides whether to keep `HOLD`, downgrade to limited live, or reject launch.
5. Post-incident report updates `LAUNCH-READINESS.md` and `launch-evidence.json` before any retry.

## Explicit No-Auto-Deploy Rule

Production deployment must not run from `push`, `pull_request`, `schedule`, repository variable changes, or dependency installation side effects. The only approved production path is manual `workflow_dispatch` with a confirmation phrase and protected `production` environment approval.
