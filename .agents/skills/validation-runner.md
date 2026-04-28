# Skill: Validation Runner

## Purpose

Run validation in the correct order and report actual results.
Never claim success without running the commands and observing output.

## Trigger

Run after every set of edits, before committing, and before reporting task completion.

---

## Hard Rules

1. Use the lockfile to determine the package manager — do not guess.
2. Do not invent script names — read them from `package.json` or equivalent.
3. If a command fails, report the actual error output, not a summary.
4. If a validation step does not exist, mark it `UNVERIFIED` with a reason.
5. Do not skip steps unless they are genuinely unavailable.
6. Do not mark a task `VERIFIED` if any validation step failed or was skipped.

---

## Package Manager Detection

```bash
if [ -f "bun.lockb" ]; then
  PM="bun"
elif [ -f "pnpm-lock.yaml" ]; then
  PM="pnpm"
elif [ -f "yarn.lock" ]; then
  PM="yarn"
elif [ -f "package-lock.json" ]; then
  PM="npm"
else
  PM="unknown"
fi
echo "Package manager: $PM"
```

---

## Validation Order

Run in this sequence. Stop and report on first failure unless instructed otherwise.

### 1. Install

```bash
# npm
npm ci

# yarn
yarn install --frozen-lockfile

# pnpm
pnpm install --frozen-lockfile

# bun
bun install --frozen-lockfile
```

Do not use `npm install` (without `ci`) — it may update the lockfile.

### 2. Type Check

```bash
# TypeScript
npx tsc --noEmit

# Or via package.json script
npm run typecheck
```

### 3. Lint

```bash
npm run lint
# or
npx eslint src/
```

### 4. Test

```bash
npm test
# or
npm run test
```

Record:
- total tests
- passed
- failed
- skipped

### 5. Build

```bash
npm run build
```

Check that build output directory exists and is non-empty:

```bash
ls dist/ || ls build/ || ls .next/ || echo "BUILD OUTPUT NOT FOUND"
```

---

## Validation Report Format

```
PACKAGE MANAGER:  [detected package manager]
INSTALL:          [PASS | FAIL | SKIPPED — reason]
TYPECHECK:        [PASS | FAIL | SKIPPED — reason]
LINT:             [PASS | FAIL | SKIPPED — reason]
TEST:             [PASS x/y | FAIL x/y | UNVERIFIED — reason]
BUILD:            [PASS | FAIL | SKIPPED — reason]
OVERALL:          [VERIFIED | UNVERIFIED | BLOCKED]
```

`OVERALL: VERIFIED` requires all available steps to show `PASS`.
`OVERALL: UNVERIFIED` means at least one step was skipped or unavailable.
`OVERALL: BLOCKED` means at least one step failed.

---

## When No Scripts Exist

If `package.json` has no `test`, `lint`, or `build` scripts:

```
VALIDATION: UNVERIFIED — no validation scripts found in package.json.
Scripts present: [list what is there]
```

Do not run arbitrary commands to compensate.
