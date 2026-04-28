# Skill: Repo Discovery

## Purpose

Understand the repository fully before making any changes.

## Trigger

Run at the start of every task, before opening or editing any file.
If the repository contains an archive as its primary source, run
`.agents/skills/repo-recovery.md` first, then re-run this skill.

---

## Hard Rules

1. Do not assume the package manager — read the lockfile.
2. Do not invent validation scripts — read `package.json` or equivalent.
3. Do not touch secrets or `.env` files during discovery.
4. Do not change CI configuration unless the task explicitly requires it.
5. Do not proceed with edits if the repository is only an archive; trigger
   repo-recovery first.

---

## Inspection Checklist

Run these in order:

```bash
# 1. Root structure
ls -la

# 2. Git state
git status
git log --oneline -5
git branch

# 3. Package manager detection
ls package-lock.json yarn.lock pnpm-lock.yaml bun.lockb 2>/dev/null

# 4. Project configuration
cat package.json 2>/dev/null || echo "NOT FOUND"
cat tsconfig.json 2>/dev/null || echo "NOT FOUND"
cat pyproject.toml 2>/dev/null || echo "NOT FOUND"
cat Cargo.toml 2>/dev/null || echo "NOT FOUND"

# 5. CI/CD
ls .github/workflows/ 2>/dev/null || echo "NO WORKFLOWS"
cat .github/workflows/*.yml 2>/dev/null | head -80

# 6. Governance
cat CODEOWNERS 2>/dev/null || echo "NOT FOUND"
cat .gitignore 2>/dev/null | head -30
cat .env.example 2>/dev/null || echo "NOT FOUND"

# 7. Source structure
ls src/ 2>/dev/null || echo "NO src/"
ls tests/ test/ __tests__/ spec/ 2>/dev/null || echo "NO TEST DIRS"

# 8. Docker / deployment
ls Dockerfile docker-compose* 2>/dev/null || echo "NO DOCKER"
```

---

## Required Output

Before editing any file, produce this report:

```
REPOSITORY:        [name and purpose based on README]
PACKAGE MANAGER:   [npm | yarn | pnpm | bun | pip | cargo | unknown]
RUNTIME:           [node version, python version, rust version, etc.]
SOURCE ROOTS:      [directories containing primary source code]
TEST ROOTS:        [directories containing tests]
VALIDATION SCRIPTS:[exact scripts from package.json or equivalent]
CI:                [workflow files and their trigger conditions]
GOVERNANCE FILES:  [CODEOWNERS, branch protection assumptions]
RISK FILES:        [.env, secrets, deployment configs, workflow files]
PLANNED CHANGES:   [what this task will modify — be specific]
```

All fields are required. Use `NOT FOUND` or `NONE` rather than omitting a field.

---

## Classification

After producing the report, classify the repository state:

| State | Meaning |
|---|---|
| `READY` | Source files tracked, validation available |
| `RECOVERY_NEEDED` | Archive present as primary source |
| `PARTIAL` | Some source tracked but gaps exist |
| `UNKNOWN` | Cannot determine without more information |

Do not proceed with a feature task if state is `RECOVERY_NEEDED`.
