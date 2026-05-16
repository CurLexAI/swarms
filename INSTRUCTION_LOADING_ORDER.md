# INSTRUCTION_LOADING_ORDER

Purpose: Define deterministic instruction-loading precedence to avoid instruction sprawl and conflicting execution behavior.
When to load: Always load this file first before selecting any optional mode/domain/profile instructions.

## Mandatory loading sequence

1. Always load **Kernel** instructions.
2. Always load **Sovereignty**, **Connector**, and **Execution** policies.
3. Load **one Mode only** based on the active task.
4. Load **Domain files only** when directly relevant to task scope.
5. Load **Agent Profile** only when acting as that specific agent.
6. Load **Templates** only for output formatting (not as background reasoning context).

## Conflict precedence rule

When instructions conflict, use this strict precedence (highest to lowest):

1. System instructions
2. Safety rules
3. Kernel
4. Policies
5. Project files
6. Mode files
7. Domain files
8. Agent profiles
9. User preference

## Loading guardrails

- Do not bulk-load all instruction files in one pass.
- Do not activate more than one mode simultaneously unless a policy explicitly requires it.
- Treat templates as render targets, not decision logic.
- If conflict cannot be resolved using the precedence rule, stop and report `CONFLICTED`.
