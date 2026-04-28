# Skill: Safe Edit Planning

## Purpose

Force the agent to declare and bound the scope of edits before touching any file.
Prevents scope creep, accidental structural changes, and unauthorized modifications.

## Trigger

Run after repo-discovery and before any file edit.

---

## Hard Rules

1. List every file expected to change before changing any of them.
2. Distinguish structural changes from behavioral changes.
3. Do not expand scope beyond what the task description specifies.
4. Do not touch deployment, secrets, or CI/CD unless the task explicitly requires it.
5. Do not combine a refactor with a feature or a bug fix in the same commit.
6. If the required change touches more than 10 files, pause and report before proceeding.

---

## Change Classification

Before editing, classify every planned change:

| Type | Definition | Requires Explicit Authorization |
|---|---|---|
| `BEHAVIORAL` | Changes runtime behavior, output, or API contracts | Yes — confirm before proceeding |
| `STRUCTURAL` | Moves, renames, or reorganizes files without changing behavior | Yes — confirm before proceeding |
| `ADDITIVE` | Adds new files or functions without touching existing behavior | No — proceed |
| `CORRECTIVE` | Fixes a bug in existing behavior to match documented intent | No — proceed |
| `COSMETIC` | Formatting, whitespace, comments only | No — proceed |

---

## Pre-Edit Declaration

Before editing, produce this report:

```
TASK:           [one sentence description of the task]
CHANGE TYPE:    [BEHAVIORAL | STRUCTURAL | ADDITIVE | CORRECTIVE | COSMETIC]
FILES TO EDIT:  [exact list of files that will change]
FILES TO ADD:   [exact list of new files]
FILES TO DELETE:[exact list of files to remove]
OUT OF SCOPE:   [explicit list of things this task will NOT touch]
RISK:           [what could break if this change is wrong]
```

---

## Scope Boundaries

These areas require explicit task authorization before editing:

- `.github/workflows/` — CI/CD pipelines
- `CODEOWNERS` — review governance
- `package.json` dependencies section — dependency management
- Any `*.env` or secrets file
- Database migration files
- Public API contracts (REST endpoints, exported types, SDK interfaces)
- Shared configuration that affects multiple environments

If the task does not mention these areas, do not touch them even if you notice
issues. Note the issue in the `RISKS` field of the final report instead.

---

## Minimum Diff Principle

Prefer the smallest correct change. If two approaches fix the same issue:

- Choose the one with fewer lines changed.
- Choose the one that does not rename symbols.
- Choose the one that does not move files.
- Choose the one that does not introduce new dependencies.

A larger change requires a larger justification.
