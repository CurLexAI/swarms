# Integrations Control-Plane Gates

## Verdict

VERIFIED: Copilot cloud agent is not required for this repository workflow. The approved execution path is GitHub Issue → Codex/Claude/local engineer → PR → CI → review.

## Workflow classification

VERIFIED: The repository workflows are separated into the following operational buckets by source inspection.

| Bucket | Workflows | Rule |
|---|---|---|
| No-secrets preflight | `aegis-gate.yml`, `aegis-mcp-gateway.yml`, `constitutional-compliance.yml`, `secret-scan.yml`, `frontend-sri.yml`, `copilot-setup-steps.yml` | Must not require private runtime secrets. |
| Manual gated deploy / runtime smoke | `modal-deploy.yml`, `modal-runtime-activation.yml`, `smoke-modal.yml`, `qarar-fastconnect-deploy.yml`, `local-model-smoke.yml` | Requires explicit dispatch and/or repository secrets; no production deploy is implied by source changes. |
| Agent review with optional secrets | `agent-review.yml`, `bayyinah-swe.yml`, `mihwar-swe.yml`, `free-birds-swe.yml`, `opencode.yml` | Missing secrets produce `UNVERIFIED`/skipped review instead of source-code success claims. |
| Evidence/compliance preflight | `pdpl-article22-ingestion.yml` | Validates local evidence artifacts only; do not claim regulatory compliance without cited evidence. |

## Render boundary

VERIFIED: `render.yaml` defines the Modal MCP Gateway service under `.agents/mcp/modal-mcp`, with `npm ci --include=dev && npm run build`, `node dist/server.js`, and `/healthz`.

VERIFIED: Render deployment is manual-gated by `autoDeploy: false` and uses `sync: false` for private tokens/endpoints. Do not add deploy hooks, plaintext endpoint URLs, or GitHub Variables as secret substitutes.

## Modal / Qdrant boundary

VERIFIED: `modal/qarar_rag_infra.py` keeps Qdrant on loopback inside the Modal container and exposes only health plus the HMAC-protected snapshot operation. It does not expose public Qdrant REST collection routes, and Modal Volume is mounted only at `/snapshots`, not as live Qdrant storage.

## MCP boundary

VERIFIED: `.github/copilot/mcp.json` defaults to `.agents/mcp/server_offline.py` through `python3` and does not define live endpoint environment variables. Live Mihwar/Bayyinah MCP configuration remains a separate, manually reviewed activation path.

## Aegis and secret-scan boundary

VERIFIED: `scripts/security/static_audit.py` is pure Python and does not depend on `rg` or external secret-scanning binaries. A finding returns a non-zero exit code.

VERIFIED: Aegis remains fail-closed: repository controls and Python tests must pass before it returns success. Missing local dependencies are an environment blocker, not a reason to weaken the gate.

## Remaining risks

UNVERIFIED: Live Render, Modal, Mihwar, Bayyinah, and Copilot cloud-agent availability were not tested because this change intentionally avoids external services and secrets.

UNVERIFIED: GitHub org-level Copilot cloud-agent assignment state was not queried in this PR; use a user-to-server token and the GraphQL suggestedActors query from the issue if needed.

## Merge recommendation

INFERRED: Merge only after CI confirms the no-secrets preflight and unit gates. Do not deploy from this PR.
