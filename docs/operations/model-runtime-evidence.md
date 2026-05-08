# Model Runtime Evidence

## Scope
- VERIFIED: This document describes runtime evidence for the currently tracked agent runtime surfaces in this repository (`.agents/modal_app.py`, `.agents/config/agents.yaml`, `.agents/router/*`).
- INFERRED: Values not explicitly declared in code (for example retries or fallback chains) are inferred from control-flow behavior.
- UNVERIFIED: Staging runtime telemetry (actual p50/p95/error-rate) and live request/response traces are not stored in-repo and are therefore marked unverified until captured from staging logs/metrics backends.

## Runtime Matrix (declaration vs implementation)

| Runtime Alias | Model Name | Internal Endpoint | Runtime Region | Timeout | Fallback Chain | Retries Policy | Evidence |
|---|---|---|---|---:|---|---|---|
| MihwarAgent | `deepseek-ai/DeepSeek-Coder-V2-Instruct` | Modal FastAPI label `mihwar-generate` (`mihwar_generate_web`) and class method `MihwarAgent.generate` | UNVERIFIED (region not declared in repository code/config) | 300s (`@app.cls`) / 360s (`@app.function`) | INFERRED: none in function path; unauthorized returns error payload | INFERRED: none declared (single execution path) | `.agents/modal_app.py` |
| BayyinahAgent | `Qwen/Qwen2.5-Coder-32B-Instruct` | Modal FastAPI label `bayyinah-review` (`bayyinah_review_web`) and class method `BayyinahAgent.review` | UNVERIFIED (region not declared in repository code/config) | 120s (`@app.cls`) / 180s (`@app.function`) | INFERRED: none in function path; unauthorized returns blocked payload | INFERRED: none declared (single execution path) | `.agents/modal_app.py` |
| Qarar Router (policy router) | Route target depends on task profile (`mihwar`, `bayyinah`, `gpt-current`, `claude-*`) | In-process policy entrypoint `build_execution_plan` + `choose_route` (no HTTP endpoint in repo) | UNVERIFIED (exec environment specific) | N/A (not a remote endpoint in this repository layer) | VERIFIED: critical/legal→Anthropic; multimodal/fast-draft→OpenAI; coding/review/agent-creation→Modal | VERIFIED: no automatic retry logic in router modules | `.agents/router/model_router.py`, `.agents/router/model_policy_engine.py` |

## Config-to-Implementation Traceability

### Mihwar
- VERIFIED: Config declares model id `deepseek-ai/DeepSeek-Coder-V2-Instruct` and endpoint alias `MihwarAgent` with timeout 300 seconds.
- VERIFIED: Modal implementation sets `MIHWAR_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Instruct"`, class timeout `300`, and HTTP function timeout `360` for `mihwar-generate`.

### Bayyinah
- VERIFIED: Config declares model id `Qwen/Qwen2.5-Coder-32B-Instruct` and endpoint alias `BayyinahAgent` with timeout 120 seconds.
- VERIFIED: Modal implementation sets `BAYYINAH_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"`, class timeout `120`, and HTTP function timeout `180` for `bayyinah-review`.

### Qarar Router
- VERIFIED: Router execution plan delegates to route provider/model from deterministic policy engine.
- VERIFIED: For non-`modal_vllm` providers, `primary_agent_id` is set to `qarar-router`, confirming this layer is a policy/dispatch component, not a model executor.

## SLO Evidence Table (Actual runtime measurement)

> Requirement states "actual SLO"; repository currently lacks committed staging telemetry snapshots. The table below is explicitly populated as UNVERIFIED pending logs/metrics extraction.

| Surface | p50 Latency | p95 Latency | Error Rate | Measurement Source | Status |
|---|---:|---:|---:|---|---|
| Mihwar (`mihwar-generate`) | UNVERIFIED | UNVERIFIED | UNVERIFIED | Staging endpoint access logs + metrics backend (not present in repository) | UNVERIFIED_RUNTIME |
| Bayyinah (`bayyinah-review`) | UNVERIFIED | UNVERIFIED | UNVERIFIED | Staging endpoint access logs + metrics backend (not present in repository) | UNVERIFIED_RUNTIME |
| Qarar Router policy path | UNVERIFIED | UNVERIFIED | UNVERIFIED | Application request traces around `build_execution_plan` (not present in repository) | UNVERIFIED_RUNTIME |

## Qwen3 Router Verification (staging)

- VERIFIED: No `Qwen3 Router` runtime object/route identifier exists in the current repository sources under `.agents/router/` and `.agents/modal_app.py`.
- INFERRED: The requested `Qwen3 Router` likely refers to an external staging deployment or another repository/runtime not committed here.
- BLOCKED (`UNVERIFIED_RUNTIME`): Short staging request/response evidence cannot be produced from repository content alone.

### Required staging evidence format to close this gap
1. Request sample (redacted): timestamp, route, normalized task profile inputs.
2. Response sample (redacted): selected provider/model + reviewer gate decision.
3. Correlation id linking request/response to staging logs or metrics query.

Until these are captured from staging, routing behavior for a `Qwen3 Router` remains `UNVERIFIED` in this repository context.

## Execution Verdict
- Status: CHANGED_BUT_NOT_VERIFIED
- Scope: Create `docs/operations/model-runtime-evidence.md` with declaration-to-implementation mapping and runtime evidence status.
- Canonical Path: `.agents/modal_app.py`, `.agents/config/agents.yaml`, `.agents/router/model_router.py`, `.agents/router/model_policy_engine.py`.
- Files Touched: `docs/operations/model-runtime-evidence.md`.
- Blockers: `UNVERIFIED_RUNTIME` (staging logs/metrics and Qwen3 staging traces unavailable in-repo).
- Hot Surface Risk: low (documentation-only change; no runtime code path modified).
- What Was Actually Changed: Added operational evidence document with explicit VERIFIED/INFERRED/UNVERIFIED separation.
- What Was Actually Verified: repository declarations and routing logic only.
- What Remains Unverified: live staging SLO numbers and Qwen3 router request/response evidence.
- Next Valid Action: Export staging logs/metrics and append measured p50/p95/error-rate + redacted routing traces.
