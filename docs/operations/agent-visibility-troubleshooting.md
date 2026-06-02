# Agent Visibility Troubleshooting (Factory + Repo)

## What exists in this repository

This repository currently defines **2 private coding agents** in `.agents/config/agents.yaml`:
- `mihwar`
- `bayyinah`

These are GitHub-review automation agents, not iOS ChatGPT model-menu entries.

## Why you only see Claude/Codex/Copilot in mobile UI

The mobile UI list in the screenshots is the **client-side selectable assistants**.
It does not auto-enumerate every private backend agent defined in this repository.

## Why Mihwar appears as skipped in checks

In `.github/workflows/agent-review.yml`, Mihwar job runs only when:
- Bayyinah outputs `REQUEST_CHANGES`.

So if Bayyinah is `APPROVE` or a skip path is taken, Mihwar is expected to skip.

## Secrets required for live remote agent calls

The workflow requires these secrets for live inference path:
- `BAYYINAH_ENDPOINT`
- `MIHWAR_ENDPOINT`
- `BAYYINAH_API_TOKEN`
- `MIHWAR_API_TOKEN`

If missing, workflows intentionally report UNVERIFIED behavior and skip remote calls. Configure these as an operator follow-up after merge; a documentation PR cannot prove GitHub Secrets were added.

## Fast verification commands

```bash
bash scripts/commander/agent-presence-gate.sh
python .agents/invoke.py info
```

## Scope clarification for "150+ agents"

If your "150 agents" are from another platform/workspace/provider, they are not currently imported into this repository config.
You need a separate synchronization registry or adapter bridge to expose them here.
