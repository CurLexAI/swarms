# Qarar/Bayyinah Secrets Manifest

This manifest records required secret **names only**. Secret values, endpoint URLs, bearer tokens, cookies, and authorization headers must never be committed or printed.

## Required for Modal Deployment

| Secret Name | Purpose | Required Before | Validation Rule |
|---|---|---|---|
| `MODAL_TOKEN_ID` | Modal CLI authentication identity | Modal deploy | Must be present in approved Actions/Modal secret store. |
| `MODAL_TOKEN_SECRET` | Modal CLI authentication secret | Modal deploy | Must be present in approved Actions/Modal secret store. |
| `HF_TOKEN` | Hugging Face model access inside Modal runtime | Modal model load | Must be stored in Modal secret `huggingface-secret`; value not logged. |
| `MIHWAR_MODEL_REVISION` | Pinned Mihwar model revision | Modal model load | Must be a full approved revision identifier. |
| `BAYYINAH_MODEL_REVISION` | Pinned Bayyinah model revision | Modal model load | Must be a full approved revision identifier. |
| `MIHWAR_REMOTE_CODE_ACK` | Explicit remote-code acknowledgement if required by model policy | Modal model load | Must be configured only after security approval. |
| `BAYYINAH_REMOTE_CODE_ACK` | Explicit remote-code acknowledgement if required by model policy | Modal model load | Must be configured only after security approval. |

## Required for Endpoint Smoke and PR Gate

| Secret Name | Purpose | Required Before | Validation Rule |
|---|---|---|---|
| `BAYYINAH_ENDPOINT` | Private Bayyinah endpoint location | Endpoint smoke / PR review | Name may be logged; value must be masked and never exposed to browser code. |
| `MIHWAR_ENDPOINT` | Private Mihwar endpoint location | Endpoint smoke / fix suggestions | Name may be logged; value must be masked and never exposed to browser code. |
| `BAYYINAH_API_TOKEN` | Bearer token for Bayyinah endpoint | Endpoint smoke / PR review | Must be present; invalid-token smoke must fail. |
| `MIHWAR_API_TOKEN` | Bearer token for Mihwar endpoint | Endpoint smoke / fix suggestions | Must be present; invalid-token smoke must fail. |
| `GITHUB_TOKEN` | GitHub PR comment token supplied by Actions | Bayyinah PR gate | Use default Actions token only; do not hardcode. |

## Required for Control Boundary and Audit

| Secret Name | Purpose | Required Before | Validation Rule |
|---|---|---|---|
| `MIHWAR_HMAC_SECRET` | Internal Mihwar HMAC boundary | Control boundary | Must be present for authenticated control actions. |
| `QARAR_RAG_HMAC_SECRET` | Qarar RAG HMAC boundary | Control boundary / RAG path | Must be present before RAG control traffic. |
| `MCP_BEARER_TOKEN` | MCP authorization boundary | MCP control path | Must be present before live MCP operation. |
| `SMOKE_TEST_TOKEN` | Non-production smoke-test credential | Smoke tests | Must not grant destructive access. |

## Fail-Closed Rule

If any secret required for a ladder phase is absent, that phase and every later phase remain `HOLD`. Operators must validate presence by name only and must not echo values or authorization headers.
