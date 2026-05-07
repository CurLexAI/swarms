# Secrets Policy

Authoritative policy for secrets used by the Mihwar/Bayyinah agent
pipeline and the Codex Commander gates. **This file documents intent and
boundaries only — no secret values are stored here.**

## 1. Required Secrets

| Name                  | Scope                | Used by                                              | Required for |
|-----------------------|----------------------|------------------------------------------------------|--------------|
| `BAYYINAH_ENDPOINT`   | Repository / Org     | `.github/workflows/agent-review.yml` → bayyinah step | Bayyinah review run |
| `MIHWAR_ENDPOINT`     | Repository / Org     | `.github/workflows/agent-review.yml` → mihwar step   | Mihwar fix-suggest run |
| `AGENT_API_TOKEN`     | Repository / Org     | Both workflow steps; `.agents/pr_review.py`          | Authenticating to Modal endpoints |
| `GITHUB_TOKEN`        | GitHub-managed       | `.agents/pr_review.py` (post review comments)        | Provided automatically by Actions |

The following secrets are referenced in deployment plans but MUST NOT be
introduced into this repository until the corresponding deploy PR is
opened with a green `modal-boundary-gate` and an Operator approval:

| Name                    | Intended use                              |
|-------------------------|-------------------------------------------|
| `MODAL_TOKEN`           | Future: deploy Mihwar/Bayyinah to Modal   |
| `RENDER_API_TOKEN`      | Future: deploy API surface to Render      |
| `CLOUDFLARE_API_TOKEN`  | Future: deploy edge worker / KV / Pages   |

## 2. Boundary Rules

1. Secrets are **never** committed to source. `.gitignore` and the
   `modal-boundary-gate` enforce that no `*.modal.run` URL or SDK import
   leaks into client/public surfaces.
2. Secrets are read **only** from `${{ secrets.* }}` in workflows or
   from `os.environ` inside server-side Python relays
   (`.agents/pr_review.py`). They are never injected into client bundles
   or echoed to logs.
3. The `agent-review.yml` workflow degrades gracefully when secrets are
   absent: it sets `verdict=SKIPPED_UNVERIFIED` rather than failing the
   build. This is intentional — missing secrets are not a code defect.
4. Public profile pages, marketing copy, and screenshots MUST NOT
   reference live endpoints. Use placeholders such as
   `https://<bayyinah-endpoint>` or `<bayyinah>.modal.run` only.
5. Local development uses unset env vars. Gate output of `[WARN]
   SECRET_MISSING:` is the expected and correct local state.

## 3. Adding a Secret (operator runbook)

This must be performed by a repository owner via the GitHub UI or
`gh secret set`. Claude Code, Copilot, or any automated agent MUST NOT
attempt to introduce secret material into the repository or its
configuration.

1. Mint the secret at its source (Modal dashboard, Render dashboard,
   Cloudflare dashboard, etc.).
2. In GitHub: `Settings` → `Secrets and variables` → `Actions` →
   `New repository secret`. Use the exact name from §1.
3. Re-run the `Agent Code Review` workflow on a benign PR. Confirm:
   - bayyinah step does NOT log `Bayyinah Agent UNVERIFIED`.
   - `modal-boundary-gate` still PASSes.
   - No secret material appears in any log line.
4. Record presence (not value) in
   `docs/launch-evidence/agent-launch.md` §4.

## 4. Rotation

| Secret              | Rotation cadence | Owner    |
|---------------------|------------------|----------|
| `AGENT_API_TOKEN`   | 90 days          | PENDING  |
| `BAYYINAH_ENDPOINT` | On endpoint move | PENDING  |
| `MIHWAR_ENDPOINT`   | On endpoint move | PENDING  |
| `MODAL_TOKEN`       | 90 days          | PENDING  |
| `RENDER_API_TOKEN`  | 90 days          | PENDING  |
| `CLOUDFLARE_API_TOKEN` | 90 days       | PENDING  |

After rotating, update §4 of `docs/launch-evidence/agent-launch.md`
with the new `Last rotated` date — never the value.

## 5. Incident Response

If a secret is suspected to have been logged, committed, or exposed:

1. Revoke the secret at the source provider immediately.
2. Replace it in GitHub Actions secrets.
3. If committed: rotate, then run `git log -p` plus a secret scanner
   over the affected branch range. File an issue tagged `security`.
4. Record the incident date and resolution in this file under §6.

## 6. Incident Log

(empty)
