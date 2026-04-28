# Skill: Repo Recovery

## Purpose

Recover a broken repository into a real, reviewable, runnable Git project.

## Trigger

Use this skill when the repository contains source code as a ZIP, tar, binary
snapshot, copied project archive, or any opaque generated bundle rather than
actual tracked source files.

Current state: `LexPrim-main.zip` is present at repository root.

---

## Hard Rules

1. Do not develop features during recovery.
2. Do not merge pull requests during recovery.
3. Do not leave project source inside an archive after recovery is complete.
4. Do not delete existing governance files (`README.md`, `CODEOWNERS`,
   `.github/workflows/*`, `.gitignore`, `.env.example`) without inspecting diffs.
5. Do not claim recovery success until real source files are tracked by Git.
6. Do not run `git add .` blindly — inspect what will be staged first.

---

## Procedure

### Step 1 — Inspect repository root

```bash
ls -la
git status
git log --oneline -5
```

### Step 2 — Detect archives

Look for:

- `*.zip`
- `*.tar`
- `*.tar.gz`
- `*.tgz`
- `*.rar`
- `*.7z`

### Step 3 — Extract into a temporary directory

```bash
mkdir -p /tmp/recovery
unzip LexPrim-main.zip -d /tmp/recovery
ls /tmp/recovery
```

### Step 4 — Detect top-level structure

If the archive extracts into a single directory, list its contents:

```bash
ls /tmp/recovery/LexPrim-main/   # adjust to actual name
```

### Step 5 — Move project files to repository root

Move actual source, config, and test files. Do not move:

- hidden git internals from the archive if it contains a `.git/`
- `node_modules/`
- build artifacts (`dist/`, `build/`, `.next/`, `out/`)

```bash
# Example:
cp -r /tmp/recovery/LexPrim-main/src ./src
cp /tmp/recovery/LexPrim-main/package.json ./package.json
# ... etc
```

### Step 6 — Remove the archive from Git tracking

```bash
git rm LexPrim-main.zip
```

Or if it was never staged:

```bash
rm LexPrim-main.zip
echo "*.zip" >> .gitignore
```

### Step 7 — Preserve or merge governance files

Check whether the archive contained versions of:

- `README.md` — merge content, keep the better version
- `.github/workflows/*` — keep existing repo version unless archive is newer
- `CODEOWNERS` — keep existing repo version
- `.gitignore` — merge
- `.env.example` — keep and review

### Step 8 — Run repo-discovery

See `.agents/skills/repo-discovery.md`.

### Step 9 — Run available validation

See `.agents/skills/validation-runner.md`.

### Step 10 — Report remaining blockers

Use the standard reporting format.

---

## Success Criteria

- No project archive remains as the primary source container.
- Meaningful source files are visible in `git diff --stat`.
- `package.json`, `tsconfig.json`, source and test directories are tracked when
  present in the original project.
- Validation was run or explicitly marked `UNVERIFIED` with a reason.

---

## Final Report Format

```
VERIFIED:   [what was confirmed by running commands]
CHANGED:    [files moved, deleted, or added]
VALIDATION: [scripts run and their results, or UNVERIFIED + reason]
RISKS:      [anything uncertain or potentially destructive]
NEXT ACTION: [single next step only]
```
