# Skill: Factory Auditor

## Purpose

Determine the current readiness state of the system and identify the single
most important next action. Prevent premature activation or deployment by
requiring explicit evidence for every readiness claim.

## Trigger

Use at the start and end of recovery or milestone tasks.
Use when asked "what is the current state?" or "is the factory ready?"

---

## Hard Rules

1. Every claim must carry one of three evidence labels:
   - `VERIFIED` — confirmed by running actual commands
   - `INFERRED` — reasonable conclusion, not confirmed by command output
   - `UNVERIFIED` — not checked; must be flagged explicitly
2. Do not declare any layer `READY` based on file existence alone.
   Files must be readable, valid, and pass validation.
3. Do not combine layers in a single readiness claim.
   Each layer has its own status.
4. Report exactly one `NEXT ACTION`. Not a list. One action.
5. `ACTIVATION` or `DEPLOYMENT` recommendations require `VERIFIED` status
   on all relevant layers.

---

## System Layers for CurLexAI/swarms

Audit each layer independently:

### Layer 0: Repository State

| Check | Status |
|---|---|
| Source files tracked by Git (not archive) | ? |
| `package.json` present and readable | ? |
| `tsconfig.json` present (if TypeScript) | ? |
| Lockfile present | ? |
| `.gitignore` present | ? |

### Layer 1: Validation Infrastructure

| Check | Status |
|---|---|
| Install succeeds | ? |
| Type check passes | ? |
| Lint passes | ? |
| Tests exist | ? |
| Tests pass | ? |
| Build succeeds | ? |

### Layer 2: Governance

| Check | Status |
|---|---|
| Branch protection assumptions documented | ? |
| CI/CD workflows present | ? |
| CODEOWNERS present | ? |
| `.env.example` present | ? |
| No secrets in tracked files | ? |

### Layer 3: Agent/Swarm Configuration

| Check | Status |
|---|---|
| `AGENTS.md` present and complete | ? |
| `.agents/skills/` present with required skills | ? |
| Agent identities documented | ? |
| Network boundary policy set | ? |

### Layer 4: Domain Readiness (activate after Layer 0–3 complete)

> Not audited until previous layers are VERIFIED.

---

## Readiness States

| State | Meaning |
|---|---|
| `BLOCKED` | A hard dependency is missing or broken |
| `DEGRADED` | Running but with known gaps |
| `PARTIAL` | Some components VERIFIED, others UNVERIFIED |
| `READY` | All checks VERIFIED, no blockers |
| `UNKNOWN` | Insufficient information to assess |

---

## Current Baseline (2026-04-28)

Based on observable repository state:

```
Layer 0 — Repository State: BLOCKED
  - Source code exists only as LexPrim-main.zip
  - No package.json, tsconfig.json, or src/ tracked in Git
  - BLOCKER: repo-recovery must run before any other layer can be assessed

Layer 1 — Validation Infrastructure: UNVERIFIED
  - Cannot assess until Layer 0 is unblocked

Layer 2 — Governance: PARTIAL
  - AGENTS.md: VERIFIED (just created)
  - .agents/skills/: VERIFIED (just created)
  - CI/CD workflows: UNVERIFIED
  - CODEOWNERS: UNVERIFIED

Layer 3 — Agent/Swarm Configuration: PARTIAL
  - Core skills documented
  - Agent identity map not yet created

Layer 4 — Domain Readiness: BLOCKED
  - Depends on Layer 0–3
```

---

## Audit Report Format

```
AUDIT DATE:     [date]
AUDITOR:        [agent or human]

LAYER 0 — REPOSITORY:     [BLOCKED | DEGRADED | PARTIAL | READY | UNKNOWN]
LAYER 1 — VALIDATION:     [BLOCKED | DEGRADED | PARTIAL | READY | UNKNOWN]
LAYER 2 — GOVERNANCE:     [BLOCKED | DEGRADED | PARTIAL | READY | UNKNOWN]
LAYER 3 — AGENT CONFIG:   [BLOCKED | DEGRADED | PARTIAL | READY | UNKNOWN]
LAYER 4 — DOMAIN:         [BLOCKED | DEGRADED | PARTIAL | READY | UNKNOWN]

OVERALL:        [BLOCKED | DEGRADED | PARTIAL | READY]

VERIFIED:       [what was confirmed]
INFERRED:       [what was assumed without confirmation]
UNVERIFIED:     [what was not checked]

BLOCKERS:       [list of hard blockers]
RISKS:          [list of non-blocking risks]

NEXT ACTION:    [single next step only]
```
