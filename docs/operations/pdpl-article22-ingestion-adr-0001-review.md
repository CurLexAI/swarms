# PDPL Article 22 ingestion workflow — ADR-0001 governance review

Status: `UNVERIFIED` — flagged for review, no removal action taken.
Created: 2026-05-22
Reporter: Codex Commander discipline, claude/compliance-rag-setup-MTijg session.

## Subject

`.github/workflows/pdpl-article22-ingestion.yml` (130 lines, on `workflow_dispatch`).

## What the workflow does

1. Validates `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `AGENT_API_TOKEN` secrets are present.
2. Installs `requirements-agent.txt` and authenticates with Modal.
3. Deploys `.agents/ingest_test.py` to Modal and captures the resulting `*.modal.run` endpoint.
4. POSTs to that endpoint with `Authorization: Bearer $AGENT_API_TOKEN`.
5. Validates the JSON response asserts Qdrant collection `qarar_regulatory_test` has at least three points and a fixed semantic-search query (`نقل البيانات الشخصية خارج المملكة`) was answered.
6. Uploads `modal_deploy.log` + `ingestion_response.json` as evidence artifacts.

## Why this needs governance review

CLAUDE.md and `docs/decisions/ADR-0001-swarms-boundary.md` define forbidden content categories for this repository. Two categories are arguably triggered:

1. **RAG pipelines** — the workflow's purpose is to ingest PDPL Article 22 regulatory content into Qdrant and verify a vector-search response. That is a RAG ingestion pipeline by any reasonable definition.
2. **LexPrim/Qarar product source** — the validation step asserts the Qdrant collection name `qarar_regulatory_test`, which is a Qarar product artifact, not an agent-operations concern.

The current `adr-0001-boundary-gate.sh` does not catch this because:

- The gate's forbidden-path list enumerates `backend_fastapi/`, `src/routes/`, `src/pipeline/`, etc., but does not enumerate `.github/workflows/*ingestion*.yml` or scan workflow content for RAG vocabulary.
- The Modal SDK reference is inside a GitHub Actions step (`modal deploy ...`), which is server-side automation and therefore not blocked by `modal-boundary-gate.sh` (that gate protects client/public surfaces, not CI).

## Possible outcomes (decision belongs to repo owner / LexPrime governance)

- **Keep**: Treat the workflow as a server-side CI utility that exercises Modal end-to-end. Justifiable if the Qdrant collection is purely a smoke-test artifact and not the canonical Qarar production pipeline.
- **Move**: Relocate the workflow and its `.agents/ingest_test.py` dependency to the LexPrim/Qarar product monorepo so the ingestion pipeline is owned by the product, not by the swarms operator repo.
- **Delete**: If the workflow has never been dispatched successfully (no production claim), removing it eliminates the ADR-0001 ambiguity entirely.

## What this PR does

Nothing destructive. It only records the concern. The workflow file remains on `main` unchanged. The repo owner / Mihwer enterprise admin should pick one of the outcomes above and follow up.

## Suggested gate hardening (out of scope for this PR)

- Extend `adr-0001-boundary-gate.sh` to scan `.github/workflows/*.yml` for tokens like `qdrant`, `vector`, `embedding`, `ingest`, `rag` in step names, and require a `# ADR-0001-EXEMPT: <reason>` comment on the workflow when matched.
- Add a registry file (`docs/decisions/adr-0001-exemptions.yaml`) listing intentional exemptions with sign-off.
