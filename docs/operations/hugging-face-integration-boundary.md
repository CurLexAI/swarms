# Hugging Face Integration Boundary

## Purpose

This document defines the explicit Hugging Face boundary for the CurLexAI/swarms
agent operations repository. The boundary is intentionally disabled by default in
NO-SECRETS / OFFLINE MCP mode. A backend-only live inference adapter exists for
explicit operator activation through Hugging Face Inference Providers; it is not
used by browser/client code and does not run unless the environment enables it.

## Current Use Decision

| Capability | Status | Boundary decision |
|---|---:|---|
| Model hosting | Explicit opt-in | `.agents/providers/huggingface_provider.py` supports backend-only chat completions only when `HF_INTEGRATION_MODE=inference_providers`. |
| Model artifacts | Boundary only | Repository variables may name an approved model repository for future offline artifact synchronization. |
| Spaces | Not active | Hugging Face Spaces are not called, deployed, or embedded by this repository. |
| Offline weight synchronization | Planned boundary | Any future synchronization must run only in an approved backend runtime with secret-store credentials and human review. |

## Default Runtime Posture

- `HF_INTEGRATION_MODE=disabled` is the only supported default for local,
  CI, Copilot, and OFFLINE MCP execution.
- `HF_TOKEN` must be configured only in an approved secret store when a human
  operator explicitly authorizes artifact synchronization or backend inference.
- `HF_INTEGRATION_MODE=inference_providers` is required before the provider will
  call Hugging Face.
- `HF_INFERENCE_BASE_URL` must use `https://router.huggingface.co/v1`.
- `MIHWAR_HF_MODEL_ID` and `BAYYINAH_HF_MODEL_ID` select the approved model ids;
  optional `MIHWAR_HF_PROVIDER` / `BAYYINAH_HF_PROVIDER` suffixes may pin a
  Hugging Face Inference Provider when required by model availability.
- `HF_MODEL_REPO` may contain only a repository identifier, not a private URL or
  live inference endpoint.
- Runtime code must depend on a port/interface and receive an implementation
  through dependency injection.
- Tests must prove that Hugging Face calls remain disabled by default even when
  placeholder environment variable names exist.

## Prohibited Actions

- Do not commit Hugging Face tokens, private repository URLs, signed URLs, or
  live inference endpoints.
- Do not call the Hugging Face Inference API, Spaces, or any external model
  endpoint from browser, client, or default server code.
- Do not enable `HF_INTEGRATION_MODE=inference_providers` for PR review or
  customer/codebase data without an explicit human approval record.
- Do not enable model weight downloads from CI, local tests, or OFFLINE MCP
  without a separate reviewed runtime activation change.
- Do not use GitHub repository variables as a substitute for secrets.

## Hexagonal Architecture Boundary

The default application dependency remains the `HuggingFaceModelArtifactPort`
interface in `src/services/huggingface.ts`, which performs no network I/O.
Backend agent runtime calls use `.agents/providers/huggingface_provider.py`,
which is mocked in tests and fail-closed unless `HF_TOKEN` and
`HF_INTEGRATION_MODE=inference_providers` are configured.

## Activation Requirements

Before any Hugging Face artifact synchronization or backend inference can be enabled, operators
must provide all of the following evidence:

1. A reviewed design decision documenting data classification, model provenance,
   and allowed runtime surface.
2. Secret-store configuration for `HF_TOKEN`; the token value must never appear
   in Git, logs, pull requests, or documentation.
3. Static checks proving no client-side or public surface can reach Hugging Face.
4. Unit tests using mocks for every branch of the adapter.
5. A human approval record for any backend-only weight synchronization or
   inference job.

## Evidence Status

VERIFIED: The repository contains an offline Hugging Face port boundary plus a
backend-only, opt-in Hugging Face provider.

VERIFIED: The default application adapter does not perform network I/O, and the
backend provider refuses to run unless explicitly enabled with secret-store
credentials.

UNVERIFIED: No live Hugging Face model hosting, Spaces deployment, inference, or
weight synchronization has been executed by this repository.
