# Skill: Agent Identity Map

## Purpose

Prevent confusion between agent names, model identities, and runtime roles.
Every agent in this system has exactly one identity at each layer.
Do not mix layers when referring to an agent.

---

## The Two Coding Agents

### Agent 1 — MIHWAR (المحور)

| Layer | Value |
|---|---|
| **Persona name** | Mihwar — المحور |
| **Role** | Senior Architect & Code Generator |
| **Capability tier** | 1 (highest) |
| **Model ID** | `deepseek-ai/DeepSeek-Coder-V2-Instruct` |
| **Model family** | DeepSeek-Coder-V2 |
| **Model size** | 236B parameters (MoE, 21B active per token) |
| **Modal app** | `curlexai-mihwar` |
| **Modal class** | `MihwarAgent` |
| **GPU** | A100-80GB × 2 |
| **Inference engine** | vLLM, tensor_parallel_size=2 |
| **Temperature** | 0.1 (near-deterministic for code) |
| **Context window** | 128,000 tokens |

**What Mihwar does:**
- Receives a task description
- Plans the architecture and file structure
- Generates complete, runnable implementations
- Decomposes large tasks for revision cycles

**What Mihwar does NOT do:**
- Approve its own output
- Make deployment decisions
- Access external APIs without authorization

---

### Agent 2 — BAYYINAH (البيّنة)

| Layer | Value |
|---|---|
| **Persona name** | Bayyinah — البيّنة |
| **Role** | Code Reviewer & Validator |
| **Capability tier** | 2 |
| **Model ID** | `Qwen/Qwen2.5-Coder-32B-Instruct` |
| **Model family** | Qwen2.5-Coder |
| **Model size** | 32B parameters (dense) |
| **Modal app** | `curlexai-bayyinah` |
| **Modal class** | `BayyinahAgent` |
| **GPU** | A100-80GB × 1 |
| **Inference engine** | vLLM, tensor_parallel_size=1 |
| **Temperature** | 0.0 (maximum precision) |
| **Context window** | 131,072 tokens |

**What Bayyinah does:**
- Reviews code, diffs, and files for bugs and security issues
- Validates Mihwar's generated output
- Returns structured findings with severity labels
- Issues APPROVE or REQUEST_CHANGES verdicts

**What Bayyinah does NOT do:**
- Generate new features or implementations
- Approve code with unresolved CRITICAL or HIGH findings
- Override human review requirements

---

## Common Confusions — Prohibited Mappings

Do not use these incorrect equivalences:

| Wrong | Correct |
|---|---|
| "Mihwar is the model" | Mihwar is the agent persona; DeepSeek-Coder-V2 is the model |
| "Bayyinah is just a linter" | Bayyinah is a full code-review agent with reasoning capability |
| "Mihwar runs on the server" | Mihwar runs on Modal cloud; the server is separate |
| "Use Bayyinah for generation" | Bayyinah reviews; Mihwar generates |
| "Tier 1 = fastest" | Tier 1 = most capable; Bayyinah is actually faster per call |

---

## Collaboration Flow

```
Task
 │
 ▼
Mihwar (generates)
 │
 ▼
Bayyinah (reviews)
 │
 ├─ APPROVE ──────────────────────► Human final review ──► Merge
 │
 └─ REQUEST_CHANGES ──────────────► Mihwar (revises)
                                         │
                                         └─ (repeat, max 3 cycles)
                                              │
                                              └─ Escalate to human
```

---

## Invocation Reference

```bash
# Mihwar — generate code
python .agents/invoke.py mihwar "Add a user authentication module"

# Bayyinah — review a file
python .agents/invoke.py bayyinah --file src/auth.py

# Bayyinah — review staged changes
python .agents/invoke.py bayyinah --diff

# Full pipeline
python .agents/invoke.py pipeline "Add rate limiting to the API"

# Show agent info
python .agents/invoke.py info
```

---

## Rules for Agents Reading This File

1. Always use the persona name (Mihwar / Bayyinah) in reports, not the model ID.
2. Always use the model ID when referring to inference configuration.
3. Do not reassign a task meant for Mihwar to Bayyinah or vice versa.
4. If a new agent is added, it must appear in this map before being used.
5. The tier number indicates capability rank, not execution priority.
