# Copilot Custom Agents Runbook

## Verdict

Copilot custom agents are repository-level operating profiles. They are not model runtimes, not production deployers, and not proof that Mihwar or Bayyinah Modal endpoints are live.

## Canonical profiles

| Profile | Role | May edit files? | Runtime dependency |
| --- | --- | --- | --- |
| `.github/agents/bayyinah.md` | Review and validation | No by default | Optional MCP `bayyinah_review` |
| `.github/agents/mihwar.md` | Safe implementation | Yes when assigned | Optional MCP `mihwar_generate` |
| `.github/agents/qarar-platform-supervisor.md` | Surface governance | No by default | None |
| `.github/agents/free-birds.md` | Multi-angle review/design | No by default | Optional MCP `free_birds_*` |

## Required live runtime evidence

Do not claim live agent operation until all are true:

1. Modal workflow ran successfully.
2. `BAYYINAH_ENDPOINT` is configured.
3. `MIHWAR_ENDPOINT` is configured.
4. `AGENT_API_TOKEN` is configured.
5. Endpoint smoke returned HTTP 200 from both Bayyinah and Mihwar.
6. Bayyinah validation has no CRITICAL/HIGH blockers.

Status label when all six are confirmed: `VERIFIED_ENDPOINT_SMOKE`

## Forbidden claims

- Do not say private Modal agents appear in ChatGPT iOS model picker.
- Do not say GitHub mobile activates private model runtimes.
- Do not say Copilot custom agents prove Modal is live.
- Do not expose raw `*.modal.run` URLs to browser, frontend, or iPhone clients.
- Do not claim production readiness without `VERIFIED_ENDPOINT_SMOKE`.

## Safe usage

Use Copilot custom agents for repository work only:

- `@bayyinah` — review PRs and risky diffs.
- `@mihwar` — implement small safe fixes.
- `@qarar-platform-supervisor` — decide surface ownership and release posture.
- `@free-birds` — parallel review/design critique.

## Activation path

Run the gate locally to confirm profiles are structurally valid:

```bash
python3 scripts/commander/copilot-agent-profiles-gate.py .
```

Then trigger the Modal activation workflow manually (requires secrets):

```
.github/workflows/modal-runtime-activation.yml
```

Required final status for live runtime: `VERIFIED_ENDPOINT_SMOKE`

## Current status

```
Copilot custom agent profiles:    VERIFIED structurally
MCP tools:                        VERIFIED structurally
Modal runtime:                    UNVERIFIED — smoke not run
Production agent operation:       BLOCKED — pending endpoint evidence
```
