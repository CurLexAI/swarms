# Hugging Face Public Coding Smoke

## Purpose

Verifies that a public-only synthetic coding task can reach Hugging Face-hosted
coding models via the Inference Router and receive coherent responses from the
approved Mihwar/Bayyinah model ids.

This is **not** a proof of Mihwar, Bayyinah, Modal, MCP, or production agent readiness.

## Success marker

The only success marker for this workflow is:

```text
VERIFIED_HF_PUBLIC_SMOKE agents=mihwar,bayyinah
```

`VERIFIED_HF_PUBLIC_SMOKE` must not be confused with `VERIFIED_ENDPOINT_SMOKE`.
`VERIFIED_ENDPOINT_SMOKE` is reserved exclusively for live Mihwar/Bayyinah Modal
endpoint smoke.

## Boundary

**Allowed:**
- Synthetic public code snippets only (`tests/fixtures/synthetic_public_task.json`)
- Style, type, correctness, and basic security observations
- Read-only Hugging Face token (`HF_TOKEN`, with legacy `HF_READ_TOKEN` fallback)
- Model overrides via `MIHWAR_HF_MODEL_ID` and `BAYYINAH_HF_MODEL_ID`
- Optional Hugging Face provider suffixes via `MIHWAR_HF_PROVIDER` and `BAYYINAH_HF_PROVIDER`

**Forbidden:**
- Customer or client code
- Legal corpora or contract text
- Confidential or client-confidential material
- Secrets, API keys, passwords, tokens
- Raw production traces or logs
- Modal endpoint activation claims
- Any claim that this smoke proves `VERIFIED_ENDPOINT_SMOKE`

## Endpoint

```
https://router.huggingface.co/v1/chat/completions
```

This is the OpenAI-compatible Hugging Face Inference Router endpoint for chat
completions. It is **not** the legacy `api-inference.huggingface.co/models/…` endpoint.

## Required secret

| Secret | Scope | Where configured |
|--------|-------|-----------------|
| `HF_TOKEN` | HF read / inference | GitHub Actions environment `HF_SMOKE` or repository secret |
| `HF_READ_TOKEN` | Legacy HF read / inference fallback | GitHub Actions environment `HF_SMOKE` |

## Optional variable

| Variable | Default |
|----------|---------|
| `MIHWAR_HF_MODEL_ID` | `deepseek-ai/DeepSeek-Coder-V2-Instruct` |
| `BAYYINAH_HF_MODEL_ID` | `Qwen/Qwen2.5-Coder-32B-Instruct` |
| `MIHWAR_HF_PROVIDER` | empty (Hugging Face router chooses/defaults) |
| `BAYYINAH_HF_PROVIDER` | empty (Hugging Face router chooses/defaults) |

## Fixture safety

`scripts/hf_public_coding_smoke.py` runs `assert_public_fixture()` before every
call. It rejects any fixture containing patterns from `FORBIDDEN_PATTERNS` (secrets,
legal, customer terms in English and Arabic). The response is checked against
`forbidden_terms` and must mention at least one `allowed_topics` entry from
`.github/smoke_allowlist.yml`.

## What this smoke does NOT prove

- Mihwar or Bayyinah are reachable
- Modal deployment is live
- Any agent is activated
- Any SAMA, PDPL, or NCA compliance claim

## Position in activation sequence

```
1. post-merge stabilization (Aegis green, npm run check, npm test)
2. custom agent profiles
3. HF public coding smoke  ← this workflow
4. Modal activation preflight
5. Modal deploy + endpoint smoke (VERIFIED_ENDPOINT_SMOKE)
```
