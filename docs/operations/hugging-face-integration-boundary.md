# Hugging Face Integration Boundary

## Purpose

This document defines the explicit Hugging Face boundary for the CurLexAI/swarms
agent operations repository. The boundary is intentionally disabled by default in
NO-SECRETS / OFFLINE MCP mode and does not authorize live model inference,
Spaces execution, or remote endpoint calls.

## Current Use Decision

| Capability | Status | Boundary decision |
|---|---:|---|
| Model hosting | Not active | Hugging Face is not used as a live inference host by default. |
| Model artifacts | Boundary only | Repository variables may name an approved model repository for future offline artifact synchronization. |
| Spaces | Not active | Hugging Face Spaces are not called, deployed, or embedded by this repository. |
| Offline weight synchronization | Planned boundary | Any future synchronization must run only in an approved backend runtime with secret-store credentials and human review. |

## Default Runtime Posture

- `HF_INTEGRATION_MODE=disabled` is the only supported default for local,
  CI, Copilot, and OFFLINE MCP execution.
- `HF_TOKEN` must be configured only in an approved secret store when a human
  operator explicitly authorizes artifact synchronization.
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
- Do not enable model weight downloads from CI, local tests, or OFFLINE MCP
  without a separate reviewed runtime activation change.
- Do not use GitHub repository variables as a substitute for secrets.

## Hexagonal Architecture Boundary

The allowed application dependency is the `HuggingFaceModelArtifactPort`
interface in `src/services/huggingface.ts`. The default adapter is an offline
implementation that returns a disabled decision and performs no network I/O.
The same file includes a mock adapter for dependency-injected tests. Future live
synchronization work must add a separate adapter behind the same port, with
mocks, tests, and policy-gate evidence before activation.

## Activation Requirements

Before any future Hugging Face artifact synchronization can be enabled, operators
must provide all of the following evidence:

1. A reviewed design decision documenting data classification, model provenance,
   and allowed runtime surface.
2. Secret-store configuration for `HF_TOKEN`; the token value must never appear
   in Git, logs, pull requests, or documentation.
3. Static checks proving no client-side or public surface can reach Hugging Face.
4. Unit tests using mocks for every branch of the adapter.
5. A human approval record for any backend-only weight synchronization job.

## Evidence Status

VERIFIED: The repository contains only an offline Hugging Face port boundary and
placeholder environment variable names.

VERIFIED: The default adapter does not perform network I/O and reports a disabled
state unless a future reviewed adapter is injected.

UNVERIFIED: No live Hugging Face model hosting, Spaces deployment, or weight
synchronization has been executed by this repository.
