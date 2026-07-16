# Main Green Baseline — Corrected Agent Directive

**Status:** APPROVED WITH REQUIRED CORRECTIONS — corrections applied; this is the send-ready version.
**Date:** 2026-07-15
**Audience:** Codex / GitHub Copilot Agent (or any coding agent assigned this task).
**Working branch:** `fix/main-green-baseline` — this branch ONLY.
**PR state:** Draft at all times. Merging is forbidden. Human review is the terminal state.

> **الملخص (Arabic summary).** هذه هي النسخة المصحّحة من أمر استعادة الخط الأخضر على `main`.
> التصحيحات المدمجة: (1) استخدام `mypy --strict .` المطابق للـworkflow، (2) فصل قرار
> baseline المستودع عن قرار جاهزية الـruntime مع دلالات exit codes للبوابة `0/1/2`،
> (3) قواعد تطابق SHA الدقيقة مع GitHub Actions بدل شرط "نفس الـcommit" الحرفي،
> (4) تصنيف بوابات `scripts/commander/` قبل تشغيلها بدل التشغيل الأعمى، (5) تقييد P5
> ليكون تشخيصياً فقط. الإضافتان: فحص أمان التبعيات قبل `npm ci`، وقسم BRANCH
> PROTECTION في التقرير النهائي. المستودع قد يكون أخضر برمجياً بينما يبقى الـruntime
> في حالة HOLD بسبب غياب الأسرار — وهذا وضع مقبول ومقصود.

---

## 0. Mission

Restore a fully green **repository baseline** on `main` of `CurLexAI/swarms`: all
required GitHub Actions workflows passing, all local policy gates passing, with
minimal, reviewable changes. Runtime/production readiness is a **separate**
decision and is expected to remain HOLD (secrets are deliberately absent in this
engagement).

## 1. Hard constraints (non-negotiable)

1. All work on branch `fix/main-green-baseline`. Never push to any other branch.
2. The PR stays **Draft**. Never merge, never enable auto-merge, never mark ready
   for review yourself.
3. No deployment, no `modal deploy`, no external runtime activation, no secret
   binding, no secret echo (report presence only as `SET`/`UNSET`).
4. No external AI API calls during repository work (CLAUDE.md prohibition 4).
5. Evidence labels on every material claim: `VERIFIED`, `INFERRED`, `UNVERIFIED`,
   `SKIPPED_UNVERIFIED`, `NOT_APPLICABLE`. Never collapse skipped into pass.
6. Do not merge or leave unresolved CRITICAL or HIGH findings.
7. Respect ADR-0001: no forbidden paths, no `autoStart` flags, no product source.

## 2. Phase P0 — Preflight

### 2.1 Branch setup

```bash
git fetch origin main
git checkout -B fix/main-green-baseline origin/main
```

### 2.2 Dependency installation preflight (REQUIRED before any `npm ci`)

```bash
node -e 'const p=require("./package.json"); console.log(JSON.stringify(p.scripts ?? {}, null, 2))'
npm ci --include=dev --ignore-scripts
```

Lifecycle scripts (`preinstall`/`install`/`postinstall`) may be run **only** if
you prove the official workflow needs them (cite the workflow file and line) and
they pass a dependency-safety review per
`.agents/policies/dependency-build-safety.md`. Otherwise `--ignore-scripts` is
mandatory.

Note on workflow parity: the official workflows install with
`npm ci --include=dev` (no `--ignore-scripts` — VERIFIED at `main.yml:58` and
`ci-local.yml:40`). If a CI failure cannot be reproduced under
`--ignore-scripts`, a workflow-exact reinstall (`npm ci --include=dev`) is
permitted **after** the dependency-safety review passes, so local reproduction
matches CI. The safe form remains the default.

Python deps:

```bash
pip install -r requirements-agent.txt
```

## 3. Phase P1 — Evidence collection from CI

Enumerate the failing/required workflows on `main` and on the PR. The required
workflow set for the repository-baseline decision is:

- `Main CI` (`.github/workflows/main.yml`)
- `CI Local` (`.github/workflows/ci-local.yml`)
- `Aegis Security Gate` (`.github/workflows/aegis-gate.yml`)
- `Constitutional Compliance` (`.github/workflows/constitutional-compliance.yml`)
- `Qarar FastConnect — Build Preflight` (`.github/workflows/qarar-fastconnect-deploy.yml`)

For each: record run URL, conclusion, tested SHA, and the first failing step with
its exact command. Do not paraphrase failure output — quote it.

## 4. Phase P2 — Local reproduction (exact workflow commands)

Reproduce each failure with the **same command the workflow runs**, not an
approximation. In particular (VERIFIED against
`.github/workflows/constitutional-compliance.yml`):

```bash
ruff check .
mypy --strict .          # NOT `mypy .` — the workflow runs --strict
```

Plus:

```bash
python3 .agents/validate.py
python3 -m py_compile .agents/*.py
python3 -m pytest -q tests/
npm test
npm run test:security
npm run test:node
npx tsc --noEmit         # DIAGNOSTIC-ONLY, expected to fail: src/runners/ ships only
                         # agentRunner.d.ts, a tracked blocker (CLAUDE.md "Known TS blocker").
                         # Record its result as the tracked blocker — it is NOT a baseline
                         # requirement and must not be "fixed" by masking the missing module.
npm run check
```

A failure that reproduces locally is `VERIFIED`. A CI failure you cannot
reproduce locally must be recorded `UNVERIFIED` with the divergence explained —
never "fixed blind".

## 5. Phase P3 — Minimal fixes

- Smallest change that makes the failing check pass for the right reason.
- No refactors, no dependency upgrades beyond what a failing check strictly
  requires, no gate weakening (never edit a gate script to make it pass unless
  the gate itself is objectively broken — and then say so explicitly).
- Keep `.ts`/`.js` companions in sync (`npm run check` → `check:service-divergence`).
- Split unrelated fixes into separate commits with clear messages.

## 6. Phase P4 — Full local verification round

Re-run everything in P2 (including `mypy --strict .`) after fixes.

### 6.1 Commander gate classification (REQUIRED before running any gate)

Enumerate every gate under `scripts/commander/` (plus
`.agents/skills/codex-commander/scripts/codex_commander_gate.sh`) and classify
each as one of:

- `LOCAL_REQUIRED` — must run and pass locally.
- `LOCAL_OPTIONAL` — run when prerequisites exist.
- `RUNTIME_REQUIRES_SECRETS` — verify **fail-closed behavior without binding
  secrets**; never bind secrets to force a pass.
- `DEPLOYMENT_MUTATION` — do **not** run.
- `NOT_APPLICABLE` — record with a direct reason.

Do not interpret "run the remaining gates" as license for outbound network or
runtime calls. Pre-classification of the current gate inventory (re-verify each
by reading the script before running — the script text is authoritative, this
table is not):

| Gate | Pre-classification |
|---|---|
| `p0-security-test-gate.sh` | LOCAL_REQUIRED |
| `adr-0001-boundary-gate.sh` | LOCAL_REQUIRED |
| `modal-boundary-gate.sh` | LOCAL_REQUIRED |
| `agent-presence-gate.sh` | LOCAL_REQUIRED |
| `public-surface-boundary-gate.sh` | LOCAL_REQUIRED |
| `qala-audit-integrity-gate.sh` | LOCAL_REQUIRED |
| `qala-egress-residency-gate.sh` | LOCAL_REQUIRED |
| `repo-rename-gate.sh` | LOCAL_REQUIRED |
| `master-audit-gate.sh` | LOCAL_REQUIRED (chains core gates) |
| `swarm-presence-monitor.py --repo-root . --no-network` | LOCAL_REQUIRED (only with `--no-network`) |
| `copilot-agent-profiles-gate.py` | LOCAL_REQUIRED |
| `codex_commander_gate.sh` | LOCAL_REQUIRED |
| `release-readiness-gate.sh` | Special — see 6.2; run only in the secrets-unbound form |
| `agent-activation-preflight.sh` | LOCAL_OPTIONAL (required only before an activation claim; none is made here) |
| `modal-runtime-smoke.sh` | RUNTIME_REQUIRES_SECRETS (verify fail-closed; do not bind) |
| `github-repo-hardening.ps1` | DEPLOYMENT_MUTATION (mutates GitHub settings — do not run) |
| `iphone-ssh-sync-diagnostic.sh` | NOT_APPLICABLE (device-specific diagnostic) |
| `windows-tor-opsec-baseline.ps1` | NOT_APPLICABLE (Windows operator tooling) |

### 6.2 Release readiness — secrets-unbound invocation (REQUIRED form)

`release-readiness-gate.sh` is designed to return HOLD when Modal secrets or
public-surface origins are absent, and may attempt `modal deploy` / runtime
smoke if it finds secrets. Therefore run it **only** like this:

```bash
env -u BAYYINAH_ENDPOINT \
    -u MIHWAR_ENDPOINT \
    -u BAYYINAH_API_TOKEN \
    -u MIHWAR_API_TOKEN \
    -u MODAL_TOKEN_ID \
    -u MODAL_TOKEN_SECRET \
    -u PUBLIC_SURFACE_ORIGIN \
    -u PUBLIC_SURFACE_APEX \
    bash scripts/commander/release-readiness-gate.sh .
```

`PUBLIC_SURFACE_ORIGIN`/`PUBLIC_SURFACE_APEX` are also unset because the gate
performs outbound `curl` checks against them when both are present (VERIFIED at
`release-readiness-gate.sh:92-96`) — unsetting them makes the
no-outbound-network intent explicit and avoids an accidental BLOCK from an
unreachable surface.

Exit-code semantics (VERIFIED against the script):

- `1` — code/test block failure → repository baseline is **not** green; fix it.
- `2` — operational `HOLD` → acceptable for this engagement.
- `0` — full `READY`.

Acceptable result in the restoration PR:

```text
No code/test block failures.
Runtime checks: HOLD because secrets are deliberately absent.
No deployment attempted.
```

Do not let absent production secrets block the restoration of a green code
baseline — and do not bind secrets to convert HOLD into READY.

## 7. Phase P5 — Runtime source-of-truth drift (DIAGNOSTIC-ONLY)

P5 is diagnostic-only unless the runtime-source-of-truth drift directly causes a
required gate failure. Permitted changes:

- Correct an objectively false or stale statement that causes a validation gate
  to fail.
- Align a narrow adapter/config contract when required for existing tests.

Otherwise:

- Do not migrate Modal to Ollama.
- Do not rewire providers.
- Do not change runtime topology.
- Open one follow-up issue with the exact conflicting files and acceptance
  criteria, and stop there.

## 8. Phase P6 — PR and CI round

1. Push to `origin fix/main-green-baseline` (`git push -u origin fix/main-green-baseline`).
2. Open (or update) the **Draft** PR against `main`.
3. Update the branch from the latest `main` before the final round, then re-run
   all required checks.

### 8.1 SHA-matching rules (replaces the naive "same commit" condition)

`pull_request`-triggered workflows may test the synthetic merge ref
(`refs/pull/<PR>/merge`), not the head commit literally. The conditions are:

- The latest PR head SHA has no newer commits after the successful workflow runs.
- Every required workflow is associated with that PR revision.
- Where GitHub tests `refs/pull/<PR>/merge`, record **both** the PR head SHA and
  the tested merge SHA.
- The tested merge SHA must contain the latest PR head and the current `main` base.

## 9. Decision gate (two-tier — REQUIRED format)

Never emit a single overall READY/HOLD. Report two decisions:

```text
REPOSITORY BASELINE DECISION:
READY FOR HUMAN REVIEW | HOLD | BLOCKED

RUNTIME / PRODUCTION DECISION:
HOLD | BLOCKED | READY
```

It is a legitimate and expected outcome that:

```text
REPOSITORY BASELINE: READY FOR HUMAN REVIEW
RUNTIME / PRODUCTION: HOLD
```

because secrets and runtime smoke are deliberately absent.

READY FOR HUMAN REVIEW applies only to the repository baseline and requires:

- Python tests successful.
- Ruff successful.
- `mypy --strict .` successful.
- TypeScript validation successful — meaning the TS checks that actually gate
  CI (`npm run check`: runtime-policy check/test, service-divergence, build
  steps in Main CI). `npx tsc --noEmit` is NOT part of this requirement: it is
  the tracked "Known TS blocker" (CLAUDE.md) and is recorded as
  `UNVERIFIED`/tracked-blocker, not fixed by masking the missing
  `src/runners` module.
- Node unit/security checks successful.
- Windows Agent build successful when the project exists and is in repository
  scope (if no required workflow builds it, record `NOT_APPLICABLE` with direct
  workflow evidence).
- Main CI successful.
- CI Local successful.
- Aegis Security Gate successful.
- Constitutional Compliance successful.
- Qarar FastConnect Build Preflight successful or explicitly `NOT_APPLICABLE`
  with direct workflow evidence.
- No unresolved CRITICAL or HIGH code findings.
- Latest PR revision covered by the successful workflow runs (per §8.1).
- No required workflow is failed, skipped unexpectedly, cancelled without
  replacement, or hidden.
- No deployment or external runtime activation occurred.

Runtime/production readiness remains HOLD until separately verified through
approved secrets, endpoint smoke, token-isolation testing, and owner approval.

## 10. Final report (REQUIRED sections)

End with the `COMMANDER REPORT` block
(`.agents/skills/codex-commander/references/commander-report-template.md`) and
the repository's Execution Verdict block, plus:

### 10.1 Gate classification results

The full classification table from §6.1 with actual outcomes and evidence labels.

### 10.2 Two-tier decision

The §9 block, each line evidence-labeled.

### 10.3 Branch protection (REQUIRED — the factory-control check)

```text
BRANCH PROTECTION:
- Required checks currently configured:
- Required approving reviews:
- Direct pushes to main allowed:
- Admin bypass allowed:
- VERIFIED | UNVERIFIED | ADMIN ACTION REQUIRED
```

Restoring green tests without proving `main` rejects red merges treats the
symptom, not the factory control failure. If you lack permission to read branch
protection settings, report `ADMIN ACTION REQUIRED` — do not guess.

---

## Appendix A — Corrections log (traceability)

| # | Correction | Where applied |
|---|---|---|
| 1 | `mypy --strict .` matches the workflow, not `mypy .` | §4 (P2), §6 (P4), §9 |
| 2 | Green baseline separated from runtime launch readiness; gate exit codes `0/1/2`; secrets-unbound `env -u` invocation | §6.2, §9 |
| 3 | SHA-matching rules replace literal "same commit tested by Actions" | §8.1 |
| 4 | Commander gates classified before execution; no blind `scripts/commander/*.sh` sweep | §6.1 |
| 5 | P5 constrained to diagnostic-only; no Modal→Ollama migration, provider rewiring, or topology change | §7 |
| +1 | Dependency installation preflight (`--ignore-scripts`) | §2.2 |
| +2 | `BRANCH PROTECTION` section in the final report | §10.3 |
| R1 | Review round: `tsc --noEmit` scoped as diagnostic-only tracked blocker (not a baseline requirement); workflow-parity note on `npm ci`; `PUBLIC_SURFACE_ORIGIN`/`APEX` added to the `env -u` form | §2.2, §4, §6.2, §9 |
