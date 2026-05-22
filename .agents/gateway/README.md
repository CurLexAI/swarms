# Gateway scaffolding (ADR-0005 pending)

This directory is **scaffolding only**. It is *not* a deployable gateway.
It exists so that ADR-0005 ("Public OpenAI-Compatible LLM Gateway in
Front of Modal") can be reasoned about with a concrete artifact instead
of an abstract proposal.

## What lives here

| File | Purpose |
|---|---|
| `mcp_server.py` | FastAPI app exposing an OpenAI-compatible *shape* only. Every model-routing endpoint returns HTTP 501 with an explicit "ADR-0005 not approved" body. **No Modal endpoint URL is hardcoded. No Modal call is performed.** |
| `Dockerfile` | Minimal container that builds and runs the stub above. Tagged `swarms-gateway-stub`, not `lexprim-gateway`, to avoid colliding with any future production image name. |
| `requirements.txt` | Stub-only deps (`fastapi`, `uvicorn`). |

## What this scaffolding does *not* do

- It does not call Modal.
- It does not embed any private endpoint URL or token.
- It does not register a public DNS record.
- It does not enable Codex CLI, Claude Code, Cursor, Continue.dev, or
  OpenWebUI to reach Mihwar or Bayyinah.
- It does not advance Option C (full public exposure) in ADR-0005.
- It does not change ADR-0001, CLAUDE.md, or the codex-commander skill.

## Gating

The server refuses to start unless the operator sets
`SWARMS_GATEWAY_STUB_ACK=1` in the environment. The variable name is
deliberate: it documents that the operator has read this README and
accepts that the stub is not production. There is no production unlock.

Even when the stub is running, all model-routing endpoints (e.g.
`/v1/chat/completions`, `/v1/completions`) return HTTP 501 with:

```json
{
  "error": "ADR-0005 has not been accepted. This stub does not proxy Modal.",
  "adr": "docs/decisions/ADR-0005-public-llm-gateway.md"
}
```

## How to delete this if ADR-0005 is rejected

`rm -rf .agents/gateway/ && rm tests/test_gateway_stub.py` and update the
ADR Status line to `Rejected`. No other files reference this directory.

## How to evolve this if ADR-0005 is accepted

Do not turn the stub on by removing the 501. Open ADR-0006 first per the
ADR-0005 "Option C" checklist, then implement against that ADR's
authentication, rate-limit, and abuse-handling design.
