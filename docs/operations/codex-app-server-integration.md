# Codex App Server Integration Notes

## Scope
This document captures canonical implementation guidance for integrating `codex app-server` in product runtimes and preserving execution discipline for CurLexAI/swarms.

## Canonical Runtime Selection
- Use **Codex app-server** when embedding Codex in a rich client that needs conversation history, approvals, and streamed agent events.
- Use **Codex SDK** for CI, batch automation, and non-interactive job orchestration.

## Transport and Security Baseline
- Default transport is `stdio` (`--listen stdio://`) with newline-delimited JSON-RPC messages.
- WebSocket transport (`--listen ws://IP:PORT`) is experimental; only bind loopback (`127.0.0.1`) unless auth is explicitly configured.
- For WebSocket authentication, prefer `--ws-auth capability-token --ws-token-file /absolute/path` over passing raw tokens in command lines.
- Treat non-loopback listeners as high-risk until auth is configured and validated.

## Required JSON-RPC Handshake
Per connection, execute:
1. `initialize` request with `clientInfo`.
2. `initialized` notification.

Any request before this sequence is invalid and should be treated as protocol failure.

## Thread/Turn Minimum Flow
1. Start or resume a thread (`thread/start` or `thread/resume`).
2. Start work with `turn/start`.
3. Consume event stream (`turn/*`, `item/*`, `thread/*`) until `turn/completed`.

## Overload and Retry Behavior
- In WebSocket mode, request ingress can reject with JSON-RPC error code `-32001` and message `Server overloaded; retry later.`
- Retry with exponential backoff + jitter.

## Health Probes (WebSocket Listener)
When running a WebSocket listener, the same endpoint serves:
- `GET /readyz`: returns `200` once listener is accepting connections.
- `GET /healthz`: returns `200` only when request has no `Origin` header.
- Requests with `Origin` header return `403`.

## Compliance/Identity Requirement
Always set a stable `initialize.params.clientInfo.name` value for enterprise compliance log attribution.

## Recommended Model Discovery
Before rendering model selection in product UI, call `model/list` and honor:
- `hidden`
- `inputModalities`
- `supportedReasoningEfforts`
- `isDefault`

## Local Validation Commands
```bash
python .agents/validate.py
python -m py_compile .agents/*.py
node --test tests/*.test.js
```

## Execution Discipline Status Vocabulary
Use only:
- `VERIFIED_FIXED`
- `PARTIALLY_APPLIED`
- `CHANGED_BUT_NOT_VERIFIED`
- `BLOCKED`
- `UNVERIFIED`
- `NOT_STARTED`
- `SUPERSEDED`
- `CONFLICTED`
