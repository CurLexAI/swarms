# Secrets Manifest (names only)

This manifest lists the **names** of secrets the launch ladder requires, grouped by
the phase that first needs them. It contains **no values**. Validation is performed
by `scripts/check-secrets-manifest.py`, which reports each name as `SET`/`UNSET` from
the process environment and **fails closed** when a required secret is absent.

> Source of truth for names: `docs/launch-evidence/secrets-manifest.json`.
> Rotation posture and storage rules: `docs/secrets-policy.md`.
> Never commit values, never print tokens or endpoint auth headers, never echo lengths.

## Required vs optional

| Secret | Required | First needed in | Purpose |
|---|---|---|---|
| `AGENT_API_TOKEN` | ✅ | Endpoint smoke | Auth for Mihwar/Bayyinah Modal endpoint calls |
| `BAYYINAH_ENDPOINT` | ✅ | Endpoint smoke | Bayyinah vLLM endpoint URL (backend-only) |
| `MIHWAR_ENDPOINT` | ✅ | Endpoint smoke | Mihwar vLLM endpoint URL (backend-only) |
| `BAYYINAH_API_TOKEN` | ✅ | Bayyinah PR gate | Token for `.agents/pr_review.py` |
| `MODAL_TOKEN_ID` | ✅ | Modal deploy | Modal auth id |
| `MODAL_TOKEN_SECRET` | ✅ | Modal deploy | Modal auth secret |
| `MIHWAR_API_TOKEN` | ⬜ | Bayyinah PR gate | Mihwar fix suggestions on `REQUEST_CHANGES` |
| `HF_READ_TOKEN` | ⬜ | Local gates | Public HF coding-model smoke (PUBLIC egress only) |
| `RENDER_DEPLOY_HOOK_URL` | ⬜ | Edge deploy | Render production deploy hook (manual, gated) |
| `SONAR_TOKEN` | ⬜ | Local gates | SonarCloud analysis (non-blocking) |
| `ANTHROPIC_API_KEY` | ⬜ | Optional | External AI — only if explicitly authorized (prohibition #4) |
| `VERCEL_TOKEN` / `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` | ⬜ | Edge deploy | Public-surface deploy (out of agent-runtime scope) |

`GITHUB_TOKEN` is provided automatically by GitHub Actions and is not listed as a
managed secret.

## How to validate (names only)

```bash
# Enforce every required secret:
python3 scripts/check-secrets-manifest.py --all

# Enforce only the secrets a given phase needs (others reported, not enforced):
python3 scripts/check-secrets-manifest.py --phase endpoint-smoke
```

Exit `0` = all enforced required secrets `SET`; exit `1` = at least one `UNSET`
(fail closed); exit `2` = manifest missing/malformed.

## Current status in this environment

`VERIFIED` (`scripts/check-secrets-manifest.py --all`, exit 1): all six required
secrets report **UNSET** in the repository build environment. This is expected —
secrets live in GitHub Actions / the secret manager, not in the repo or this
container. The fail-closed result is correct and gates Phases 5+ until secrets are
provisioned by the owner.
