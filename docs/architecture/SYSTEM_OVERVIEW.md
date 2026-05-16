# System Overview

## Core Systems

### Bayyinah
Validation and verification layer.

### Mihwar
Orchestration and routing layer.

### Joker
Coordinator and execution planner.

## Principles

- Saudi sovereign-first AI.
- Compliance-aware architecture.
- Minimal external dependency exposure.
- Strict separation between orchestration and inference.
- Modal used as inference execution layer only.
- No autonomous agents inside repository.
- Human-approved production changes only.

## Deployment Philosophy

- Experiments isolated from production.
- Infrastructure changes require confirmation.
- Model routing must remain auditable.
- Arabic reasoning quality prioritized over benchmark vanity.

## Coding Standards

- TypeScript strict.
- No any.
- Result<T, E> preferred.
- Small safe changes over broad rewrites.
