# Agent Capacity Plan — 200-Agent Target Architecture

> STATUS: DESIGN / TARGET — UNVERIFIED in runtime.
> registry.yaml today = ~24-29 VERIFIED agents. This plan does NOT alter runtime.

## Stratification
| Layer | Role | Target | % |
|---|---|--:|--:|
| Founder-Facing | direct owner UI, behind escalation-gate | 20 | 10% |
| Client-Facing | LexPrim/Qarar users, no secrets/main | 70 | 35% |
| Worker | silent sandboxed execution | 100 | 50% |
| Control Plane | router+audit+gates, fail-closed | 10 | 5% |
| Total | | 200 | 100% |

## Model Allocation (target)
| Model | Endpoint | ~N | Use |
|---|---|--:|---|
| Qwen2.5-Coder-32B | BAYYINAH_ENDPOINT | 95 | review birds, chat, repo review |
| DeepSeek-Coder-V2 | MIHWAR_ENDPOINT | 55 | reasoning birds, legal, architecture |
| Local Ollama | OLLAMA_BASE_URL | 40 | RAG, intake, sandbox |
| Router/Policy | local | 10 | control plane |

External AI = DENIED (ALLOW_EXTERNAL_AI=false; transports UNVERIFIED).

Verification: UNVERIFIED in runtime. Counts are design targets only.
