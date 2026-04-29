# Policy: Dependency and Build Safety

## Purpose

Prevent supply-chain risk, accidental artifact commits, and unsafe dependency changes.

---

## Hard Rules

1. Do not install dependencies unless validation requires it.
2. Prefer lockfile-respecting commands: `npm ci`, `pnpm install --frozen-lockfile`, `yarn install --frozen-lockfile`, or pinned Python requirements.
3. Do not run lifecycle scripts from untrusted dependency changes without review.
4. Do not delete lockfiles to force installation.
5. Do not commit `node_modules`, `.venv`, build caches, `dist`, `.next`, `build`, coverage output, or downloaded model weights.
6. Dependency additions/removals require human review before merge.
7. If a build requires network, document the domains contacted.

---

## Review Checklist

- Lockfile changed with dependency manifest.
- New package purpose is documented.
- No postinstall/build script executes arbitrary downloads.
- No native binary download from unknown domains.
- No version range is broadened unnecessarily.
- No package introduces external AI/API calls in tests or build.

---

## Report Fields

```text
DEPENDENCIES_CHANGED: YES/NO
LOCKFILE_STATUS: PRESENT/MISSING/N/A
LIFECYCLE_SCRIPTS_REVIEWED: YES/NO/N/A
BUILD_ARTIFACTS_COMMITTED: YES/NO
ACTION: summary
```
