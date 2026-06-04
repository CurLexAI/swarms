# Modal Endpoint Smoke Test — 2026-05-23

> **Purpose:** Verify that `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT`, and
> endpoint-specific runtime tokens are correctly bound in GitHub Actions Repository
> Secrets, and that Modal endpoints respond to real inference requests.
>
> **Method:** This file exists to trigger `agent-review.yml` on a PR.
> The workflow's `bayyinah-review` job will either:
>
> - Complete in < 30 seconds → **SECRETS_MISSING** (secrets unset)
> - Complete in 60–300 seconds → **VERIFIED** (Modal endpoint responded)
>
> Mihwar fix-suggest is conditional on Bayyinah verdict
> `REQUEST_CHANGES`, so a smoke PR does not always exercise it. To
> verify Mihwar directly, dispatch `Modal Smoke Probe`
> (`.github/workflows/smoke-modal.yml`) from Actions → Run workflow.

## Provenance

| Field | Value |
|---|---|
| Recorded at | 2026-05-23 |
| Trigger     | smoke-PR auto-dispatch of `agent-review.yml` |
| Branch      | `claude/smoke-test-modal-secrets` |

## Expected outcomes

- `bayyinah-review` job duration ≥ 60s and verdict ≠ `UNVERIFIED`.
- No `*.modal.run` URL appears in the run logs (masked via `::add-mask::`).
- No secret value appears in any log line.

## Next step after PR closes

Whether merged or closed, update
`docs/launch-evidence/agent-launch.md` §5 (Runtime Smoke Tests) with
the observed verdict and timestamp.
