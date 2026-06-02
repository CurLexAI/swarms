# Agent Visibility Runbook (iPhone / GitHub / ChatGPT)

## Purpose

Use this runbook when private CurLexAI agents or custom models are not visible in iPhone surfaces (ChatGPT model picker, GitHub mobile UI, or MCP clients).

## VERIFIED behavior boundaries

1. ChatGPT iOS model picker only shows OpenAI-hosted chat models available to the account.
2. Private Modal models (Mihwar/Bayyinah) are backend runtime endpoints and do not appear as native model choices in ChatGPT iOS.
3. GitHub mobile file editing does not deploy or activate private model runtimes.

## Activation prerequisites (must be `SET`)

- `MIHWAR_ENDPOINT`
- `BAYYINAH_ENDPOINT`
- `BAYYINAH_API_TOKEN`
- `MIHWAR_API_TOKEN`

Never print values. Report only `SET` or `UNSET`.

## Quick diagnosis commands

```bash
git remote -v
git status --short
git branch --show-current
python3 .agents/invoke.py info
python3 .agents/validate.py
for v in MIHWAR_ENDPOINT BAYYINAH_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN; do
  if [ -n "${!v}" ]; then echo "$v=SET"; else echo "$v=UNSET"; fi
done
```

## Runtime smoke checks (backend only)

The active repository workflow for runtime activation is `.github/workflows/modal-runtime-activation.yml`; it is manually triggered with `workflow_dispatch` and supports `deploy_modal` plus `run_smoke`. After operator-managed secrets are configured, run that workflow with smoke enabled. For local trusted-shell diagnostics only, with secrets exported, run:

```bash
python3 .agents/invoke.py mihwar "Return: runtime_ok"
python3 .agents/invoke.py bayyinah --diff
```

Expected:

- Mihwar returns generation output without auth/runtime errors.
- Bayyinah returns review output without missing-env errors.

## Decision matrix

- If any required secret is `UNSET`: private agents are `UNVERIFIED` and cannot appear as active tools.
- If secrets are `SET` but invoke fails: deployment or endpoint drift is `INFERRED`; re-deploy Modal app and retest.
- If invoke passes but iPhone still shows only built-in models: behavior is `VERIFIED` (frontend picker is not the private-runtime selector).

## Operator reminder

To use sovereign private models from client surfaces, route through approved backend adapters (MCP/gateway) that call Modal server-side. Do not expose raw `*.modal.run` URLs to browser or iPhone clients.
