# Data Residency Proof

## Purpose
This document defines the canonical data-flow map and residency checkpoints for user data handled by the CurLexAI swarms operating stack.

## Canonical Data-Flow Map

```text
Browser
  ↓ (HTTPS request metadata + user payload)
Backend
  ↓ (provider API call with scoped payload)
Model Runtime
  ↓ (response payload + operational metadata)
Storage/Logs
```

## Flow Details by Segment

### 1) Browser → Backend
- Data types: request payloads, auth artifacts, IP/network metadata, user-agent, session identifiers.
- Primary processing location: backend runtime region configured by deployment.
- Residency control: ingress endpoints must be region-pinned and documented in environment inventory.

### 2) Backend → Model Runtime
- Data types: prompt payloads, task context, model parameters, correlation IDs.
- Primary processing location: depends on configured model runtime:
  - Self-hosted runtime (example: Modal/vLLM region assigned to deployment).
  - External model provider runtime (provider-controlled region, unless explicit regional control exists).
- Residency control: provider/region selection must be recorded before production use.

### 3) Model Runtime → Storage/Logs
- Data types: model outputs, status metadata, audit events, error traces.
- Primary processing location: storage and logging backends bound to configured service regions.
- Residency control: storage class and log sink region must be documented and reviewed.

## Telemetry and Third-Party Channel Inventory

All channels below require explicit owner assignment and region declaration before they can be treated as residency-safe.

| Channel | Examples | Third Party | Data Classes | Processing Location | Status |
|---|---|---|---|---|---|
| CDN / edge delivery | Static asset delivery, TLS termination | CDN vendor | IP, request headers, path/query metadata | CDN POP + vendor backbone regions | UNVERIFIED |
| Analytics | Product analytics, page events, usage counters | Analytics vendor | Event payloads, identifiers, behavioral metadata | Vendor ingestion + storage regions | UNVERIFIED |
| Error tracking | Exception traces, stack context, request breadcrumbs | Error monitoring vendor | Error payloads, possible user context | Vendor processing/storage regions | UNVERIFIED |
| Model provider hops | API gateway, inference endpoints, safety filters | Model provider | Prompts, outputs, model metadata | Provider runtime regions + subprocessors | UNVERIFIED |
| Infrastructure logs | Cloud logging, APM, audit streams | Cloud/platform vendor | Operational logs, trace IDs, infra metadata | Cloud account log regions | UNVERIFIED |

## Evidence Requirements for Residency Claims
A residency claim is publishable only when all required evidence artifacts are present:
1. Environment-region inventory (runtime, storage, log sink, CDN, model provider).
2. Active vendor DPA/terms identifying subprocessors and regions.
3. Internal control record mapping each data channel to a region.
4. Dated internal sign-off from security/compliance owner.

Without these artifacts, claim status remains `UNVERIFIED`.
