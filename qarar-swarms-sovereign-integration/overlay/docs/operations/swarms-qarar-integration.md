# Swarms x Qarar Sovereign Model Integration

## Decision

Expose Qarar sovereign models to Swarms as controlled tools, not as direct model endpoints.

The call path is:

```txt
Swarms Agent -> Qarar tool adapter -> UTE envelope -> Bayyinah controls -> Qarar sovereign model router -> append-only audit
```

This preserves Qarar's Saudi sovereign execution model while allowing Swarms to coordinate multi-agent workflows.

## Model routes

| Swarms role | Qarar task type | Sovereign model | Protocol bias |
| --- | --- | --- | --- |
| Legal reasoning agent | LEGAL_REASONING | deepseek-r1-32b | ACP unless regulated/PII |
| Local context agent | LOCAL_CONTEXT | allam-7b | MCP |
| Arabic drafting agent | ARABIC_DRAFTING | qwen-72b-arabic | ACP unless regulated/PII |
| Consensus review | CONSENSUS_REVIEW | deepseek-r1-32b plus reviewers | ANP for regulated/PII |

## Controls

1. Every request carries `traceId`, `agentId`, `taskType`, `modelId`, and `BayyinahDataContext`.
2. Production calls are evaluated by sovereign egress policy before dispatch.
3. Regulated or PII-bearing requests are routed to ANP by default.
4. Local Saudi context requests are routed to MCP by default.
5. Outputs must include confidence and source references before autonomous use.
6. Audit is append-only and hash-chain compatible.

## Python Swarms usage

```python
from qarar_swarms import create_qarar_tool

legal_reasoning_tool = create_qarar_tool(
    task_type="LEGAL_REASONING",
    agent_id="swarms.legal-reasoning-agent",
    data_class="INTERNAL",
    contains_pii=False,
    context={"authority": "SAMA"},
)

result = legal_reasoning_tool("حلل الالتزام النظامي لهذه السياسة.")
```

The adapter returns plain Python callables so it can be passed to Swarms-style `tools=[...]` APIs without binding Qarar to a fragile framework-specific class shape.

## Environment

```txt
QARAR_API_BASE_URL=https://qarar.internal
QARAR_API_TOKEN=
QARAR_API_TIMEOUT_SECONDS=30
QARAR_SWARMS_DRY_RUN=true
QARAR_DEFAULT_JURISDICTION=KSA
```

## Pinned production dependencies

```txt
python-dotenv==1.0.0
requests==2.31.0
psutil==5.9.8
swarms==5.0.0
```

## Safety boundary

This overlay does not deploy, write secrets, reset databases, or disable security middleware. It only adds integration code and tests.
