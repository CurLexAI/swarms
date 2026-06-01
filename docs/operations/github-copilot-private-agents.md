# GitHub Copilot Private Agents and CurLexAI Runtime Identity

## Current verified design

- CurLexAI private Modal-facing agents are **Mihwar**, **Bayyinah**, and **Qarar Router**.
- `.github/agents/copilot-swe.agent.md` was removed and is not a CurLexAI private Modal agent profile.
- `.agents/config/agents.yaml` is the canonical runtime source of truth.
- `agents/registry.yaml` can describe topology/fallback intent, but must not override `.agents/config/agents.yaml`.
- CurLexAI private agent profiles are **Mihwar**, **Bayyinah**, and **Qarar**.
- `.github/agents/copilot-swe.agent.md` was removed and must not be treated as a CurLexAI private agent.
- `.agents/config/agents.yaml` is the canonical runtime source of truth.
- `agents/registry.yaml` may describe topology or fallback behavior, but it must not override `.agents/config/agents.yaml`.

## Identity layers

1. **GitHub Copilot model picker**: provider UI surface controlled by GitHub.
2. **`.github/agents/*.agent.md`**: Copilot-facing repository agent profiles.
3. **`.agents/config/agents.yaml`**: canonical CurLexAI runtime agent configuration.
4. **Modal / MCP / GitHub Actions**: execution and routing layer.

## Copilot model picker boundary

- Copilot can be guided by repository agent profiles.
- Private routing can go through MCP, GitHub Actions, and Modal endpoints.
- The native Copilot model picker remains GitHub-controlled and cannot be renamed/replaced by this repository.

## Intended private roles

- **Mihwar**: orchestration, implementation planning, execution coordination.
- **Bayyinah**: verification, audit evidence checking, boundary enforcement.
- **Qarar Router**: local policy router/decision selector that routes to Mihwar and Bayyinah; it does not replace them.

## Verified state

- Repository-level generic Copilot profile file `.github/agents/copilot-swe.agent.md` is absent.
- `qarar-router` runtime is `local_policy` and routes to Mihwar/Bayyinah decision paths in canonical runtime config.
- MCP path uses `Authorization: Bearer` for authenticated requests.
- No token-in-payload transport pattern was identified in reviewed MCP paths.
- No public/client `*.modal.run` exposure was identified in reviewed client-facing surfaces.

## Unverified / blocked

- Live Modal runtime remains unverified/blocked until required endpoints/secrets/apps are configured and smoke-tested.
- Endpoint smoke tests are not proven.
- Qdrant remains `UNVERIFIED` until `qdrant-secret` exists and `.agents/ingest_test.py` succeeds.
- Commander bash gates were previously blocked by CRLF parsing on affected environments; this is a line-ending execution blocker, not policy-logic evidence.

## Risks

- **HIGH**: Runtime activation is still `UNVERIFIED` because Modal secrets/apps were intentionally not checked in this documentation-only scope.
- **MEDIUM**: CRLF normalization issues can block local bash gate execution before policy logic runs.
- **MEDIUM**: Legacy references such as `copilot_swe` in non-profile config are treated as non-canonical unless aligned to `.agents/config/agents.yaml`.

## Do not claim

- Do not claim private agents appear as native Copilot models.
- Do not claim runtime activation until Modal secrets/apps/endpoints are proven.
- Do not claim Qdrant ingestion/retrieval until `.agents/ingest_test.py` succeeds.
- The native Copilot model picker remains a GitHub-controlled provider surface.
- This repository cannot rename or replace GitHub Copilot native model dropdown entries.

## Intended private roles

- **Mihwar**: orchestration, implementation planning, and execution coordination.
- **Bayyinah**: verification, audit evidence checking, and boundary enforcement.
- **Qarar**: local policy router / decision selector that routes to Mihwar and Bayyinah; it does not replace them.

## Verified state

- Generic `copilot-swe` profile is removed.
- `qarar_router` is `local_policy` and routes to `mihwar`/`bayyinah`.
- MCP uses `Authorization: Bearer`.
- No token-in-payload matches were found.
- No public/client `*.modal.run` exposure was found in the reviewed surfaces.

## Unverified / blocked

- Modal/GitHub runtime activation remains unresolved.
- Endpoint smoke tests are not proven.
- Qdrant remains `UNVERIFIED`.
- Commander bash gates were reported blocked locally by CRLF parsing, not by known policy logic failure.

## Do not claim

- Do not claim private agents appear as native Copilot models.
- Do not claim runtime activation until Modal secrets/apps/endpoints are proven.
- Do not claim Qdrant ingestion/retrieval until `.agents/ingest_test.py` succeeds.

## Validation evidence (local)

- `python .agents/validate.py`: PASS.
- `python -m py_compile .agents/ingest_test.py .agents/modal_app.py .agents/mcp/server.py .agents/mcp/mcp_server.py .agents/mcp/openai_compat_server.py .agents/github_clone_repo.py .agents/modal_secret_smoke.py`: BLOCKED (`CONFIG_NOT_FOUND` for missing files under `.agents/` in this branch).
- `git diff --check`: PASS.
- `bash scripts/commander/agent-presence-gate.sh`: PASS, with `SECRET_MISSING` warnings for runtime secrets expected outside local runtime.
- `bash scripts/commander/modal-boundary-gate.sh .`: PASS, with `SECRET_MISSING` warnings for runtime secrets expected outside local runtime.
- `bash scripts/commander/adr-0001-boundary-gate.sh .`: PASS.
- CRLF status for commander gates: no current CRLF gate failure reproduced in this run.
