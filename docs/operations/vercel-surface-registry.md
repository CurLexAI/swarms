# Vercel Surface Registry

- **Status:** Freeze production aliases pending canonicalization
- **Owner:** CurLexAI platform operations
- **Last reviewed:** 2026-05-31
- **Decision record:** `docs/decisions/ADR-0004-canonical-platform-surfaces.md`

## Executive Rule

No production alias may point to a Vercel project that is not listed as
canonical in this registry.

## Canonical

- Production project: TBD
- Team: LexCode (candidate; not verified as final owner)
- GitHub repo: TBD
- Domain aliases: TBD
- Evidence label: `UNVERIFIED`

## Candidate Assessment

| Vercel project | Linked repository path | Evidence label | Decision |
|---|---|---|---|
| `lexnexus` | Private `MOTEB1989/lexnexus` path reported by operator | `UNVERIFIED` | Candidate canonical only after code and deployment audit. |
| `lex-nexus` | Public `Wejdan-AI/LexNexus` path reported by operator | `UNVERIFIED` | Suspect / legacy / marketing prototype until audited. |

The private `lexnexus` path is the working candidate because sensitive
production surfaces normally require private-source review, but this is not a
final production decision without code, owner, alias, and environment audit.

## Quarantined / Non-Canonical Candidates

The following project names must not receive production aliases unless they are
promoted into the Canonical section by a future audited decision:

- `lex-nexus`
- duplicate `wejdan-ai` projects
- `chatbot-ui`
- `nextjs-ai-chatbot`
- `nextjs-ai-chatbot-s4to`
- `nextjs-ai-chatbot*`
- `ai-orchestrator`
- `rsc-genui`
- `morphic-ai-answer-engine-generative-ui`

## Team Ownership Risk

Reported Vercel teams include:

- `RAGHADHAI's projects`
- `LINUX Team`
- `LexCode`

This repository has not verified Vercel team metadata. Until verified, the
platform must treat Vercel ownership as ambiguous and avoid production alias
changes.

## Freeze Policy

Production alias changes are frozen until all of the following are recorded:

1. Canonical Vercel team.
2. Canonical Vercel project.
3. Canonical GitHub repository.
4. Expected production domain aliases.
5. Owner-approved rollback path.
6. Confirmation that the project is not a duplicate, prototype, or mirrored
   copy of `CurLexAI/swarms`.

## Required Audit Before Unfreeze

Before moving any Vercel project into Canonical, record:

- Repository URL and visibility.
- Vercel team and project ID.
- Production and preview aliases.
- Environment variable inventory by name only; do not print values.
- Build command and output directory.
- Framework and runtime version.
- Last successful deployment commit.
- Rollback target.
- Security review result for public endpoints and secrets exposure.

## Deployment Prohibition

Do not use this registry as authorization to deploy. It is a freeze and
classification document. Deployment remains blocked until a future PR promotes
one project into Canonical with evidence.
