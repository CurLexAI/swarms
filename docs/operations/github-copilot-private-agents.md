# GitHub Copilot Private Agents over Modal

## Decision

GitHub Copilot's model picker cannot be renamed or replaced with CurLexAI private Modal models from this repository alone.

What this repository can provide:

1. GitHub custom agent profiles under `.github/agents/` so Copilot can operate with CurLexAI-specific roles.
2. A sovereign gateway pattern that routes private model work through Render -> Modal.
3. GitHub Actions/MCP integration points that call Mihwar and Bayyinah when secrets are configured.

## Expected UI Behavior

- Copilot's built-in model dropdown may still show GitHub-supported models such as GPT, Claude, Gemini, or similar provider models.
- CurLexAI agents should appear as custom agents/profiles where GitHub supports repository custom agents.
- If the desired UX is `@mihwar`, `@bayyinah`, or `@qarar` as chat participants, that requires a Copilot extension / GitHub App / MCP-compatible integration layer. It is not achieved by renaming the built-in model picker.

## Agent Profiles Added

| Agent | File | Purpose |
|---|---|---|
| Qarar | `.github/agents/qarar.agent.md` | orchestration, topology, routing, plans |
| Mihwar | `.github/agents/mihwar.agent.md` | coding architecture and generation |
| Bayyinah | `.github/agents/bayyinah.agent.md` | validation, security review, merge blocking |

## Runtime Routing

```text
GitHub Copilot custom agent profile
  -> repository instructions
  -> GitHub Action / MCP / Render gateway
  -> Modal sovereign runtime
  -> Mihwar / Bayyinah / Qarar model endpoint
```

Do not expose Modal endpoints to browser clients, mobile clients, or untrusted prompts.

## Required Secrets

GitHub repository or environment secrets:

```text
BAYYINAH_ENDPOINT
MIHWAR_ENDPOINT
AGENT_API_TOKEN
```

Optional gateway secrets depending on deployment:

```text
SOVEREIGN_MODAL_BASE_URL
SOVEREIGN_API_KEY
```

## Verification

Run structural checks:

```bash
find .github/agents -maxdepth 1 -type f -name '*.agent.md' -print
bash scripts/commander/agent-presence-gate.sh
```

Runtime remains `UNVERIFIED` until:

1. GitHub secrets are configured.
2. Modal endpoints are live.
3. A smoke test calls Mihwar and Bayyinah successfully.

## No-Go Claims

Do not claim:

- The Copilot model dropdown has been replaced.
- GitHub will display private Modal models as native model names.
- `@mihwar` or `@bayyinah` is available unless a chat participant/extension layer is actually installed.
- Mihwar/Bayyinah are runtime verified without endpoint smoke evidence.
