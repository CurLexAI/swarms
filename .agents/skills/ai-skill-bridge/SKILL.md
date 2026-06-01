---
name: ai-skill-bridge
description: normalize and audit reusable ai skills across gemini, codex, claude code, and chatgpt. use when importing local skills into the repository, converting skill instructions between clients, validating skill boundaries, creating skill registries, or preparing skills for activation without leaking secrets, enabling autostart, or bypassing repository gates.
---

# AI Skill Bridge

## Mission

Normalize AI assistant skills into repository-controlled playbooks.

## Hard rules

- Never copy secrets, tokens, endpoint URLs, `.env` files, local credentials, or API keys.
- Never add the `auto-start` activation flag (forbidden by ADR-0001), background activation, production deployment, or model runtime activation.
- Never claim that a skill is active in Gemini, Claude Code, Codex, or ChatGPT unless the target client has loaded it and a read-only test confirms behavior.
- Keep skills under `.agents/skills/`.
- Keep policies under `.agents/policies/`.
- Keep registries under `.agents/registries/`.
- Run repository gates before readiness claims.

## Supported clients

| Client | Source format | Repository representation |
|---|---|---|
| Gemini CLI | `~/.gemini/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` |
| Codex | repo playbook / command doctrine | `.agents/skills/<name>/SKILL.md` + scripts |
| Claude Code | `CLAUDE.md` + repo instructions | skill-compatible playbook + `CLAUDE.md` pointer |
| ChatGPT | packaged Skill directory | `.agents/skills/<name>/` source, packaged externally when needed |

## Intake process

1. Inspect source skill.
2. Confirm it has `SKILL.md`.
3. Remove local-only paths unless documented as examples.
4. Remove secrets and tokens.
5. Add compatible triggers.
6. Add risk rating.
7. Update `.agents/registries/ai-skills.registry.yaml`.
8. Run gates.

## Required report

Use:

- VERIFIED
- INFERRED
- UNVERIFIED
- BLOCKERS
- NEXT ACTION
