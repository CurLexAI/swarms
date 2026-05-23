# Agent Handbook — CurLexAI/swarms

This repository is the operating layer for CurLexAI agent tooling, review automation, and swarm activation. Every automated agent, including Codex, Claude, Copilot, and local scripts, must read this file before changing repository content.

---

## Current Operating State

`main` no longer contains `LexPrim-main.zip`. The previous archive-only blocker is closed at the repository level, but full product source recovery remains a controlled intake task whenever an archive is supplied outside Git.

Until a source archive is intentionally restored or supplied for intake, agents must treat the repository as an **agent operations repository**, not as a recovered application monorepo.

---

## Core Rule

No success claim is valid without evidence.

Use exactly one evidence label for every material claim:

- `VERIFIED` — confirmed by command output, GitHub metadata, or observable repository content.
- `INFERRED` — reasonable conclusion from evidence, but not directly confirmed.
- `UNVERIFIED` — not checked or blocked by missing access, missing secrets, missing network, or missing runtime.

Never hide failures. Never convert an inferred result into a verified result.

---

## Required Execution Order

1. **Scope Lock** — identify the exact task and the files allowed to change.
2. **Repository Discovery** — inspect repository structure before editing.
3. **Policy Check** — apply secrets, network, and dependency safety rules.
4. **Safe Edit Plan** — state what will change and what will not change.
5. **Implementation** — make the smallest complete production change.
6. **Validation** — run static checks, syntax checks, tests, or explain blockers.
7. **Report** — use the standard report template.

---

## Skills

Skills are operational playbooks. They describe *how* to perform task classes.

| Skill | File | Use |
|---|---|---|
| Task Scope Lock | `.agents/skills/00-task-scope-lock.md` | Required before broad or ambiguous tasks when present. |
| Repo Recovery | `.agents/skills/repo-recovery.md` | Use only when an archive or opaque source bundle is present. |
| Repo Discovery | `.agents/skills/repo-discovery.md` | Required before every edit. |
| Safe Edit Planning | `.agents/skills/safe-edit-planning.md` | Required before modifying files. |
| Validation Runner | `.agents/skills/validation-runner.md` | Required after changes. |
| Secure PR Review | `.agents/skills/secure-pr-review.md` | Required for PR review or merge decisions. |
| Factory Auditor | `.agents/skills/factory-auditor.md` | Use for layer readiness, launch readiness, and blocker audits. |
| Agent Identity Map | `.agents/skills/agent-identity-map.md` | Use for agent/model/role changes. |
| iPhone Command Center | `.agents/skills/iphone-command-center.md` | Use when operating this repository from iPhone through ChatGPT, SSH, GitHub, Codex, or remote runtimes. |
| HF CLI | `.agents/skills/hf-cli/SKILL.md` | Use when downloading, uploading, or managing Hugging Face Hub repos, models, datasets, spaces, or jobs via the `hf` CLI. |

If `00-task-scope-lock.md` is absent, apply the Scope Lock section in this file directly.

---

## Policies

Policies are mandatory boundaries, not optional skills.

| Policy | File | Enforcement |
|---|---|---|
| Secrets Boundary | `.agents/policies/secrets-boundary.md` | Blocks secret leaks, real credentials, and unsafe logs. |
| Network Boundary | `.agents/policies/network-boundary.md` | Blocks unauthorized network access and exfiltration. |
| Dependency Build Safety | `.agents/policies/dependency-build-safety.md` | Controls package installs, lockfiles, scripts, and build artifacts. |
| Execution Discipline Maximum | `.agents/policies/execution-discipline-maximum.md` | Enforces strict runtime-truth claims, blocker taxonomy, and status/report semantics. |

If a policy file is missing, apply the absolute prohibitions in this handbook and mark the policy check `UNVERIFIED`.

---

## Scope Lock

For broad instructions such as "execute everything", agents must prioritize in this order:

1. Fix contradictions or blockers that prevent correct operation.
2. Activate validation and safety rails.
3. Stabilize agent workflows.
4. Recover product source only when the source artifact is actually present in Git or explicitly supplied to the runtime.
5. Defer feature work until repository discovery and validation are complete.

Do not treat a broad instruction as permission to delete governance files, bypass secrets policy, or merge unvalidated changes.

---

## Work Intake Sources

This repository does not track executable work via inline `TODO`, `FIXME`, `XXX`, or `HACK` comments in source. A grep for those markers will return no real matches, and that is intentional, not an omission. Do not fabricate one to justify a change.

When asked to "implement a TODO" or otherwise pick up the next unit of work, resolve the request against these sources, in order:

1. Open issues in `CurLexAI/swarms` (`mcp__github__list_issues` with `state: OPEN`).
2. Failing checks on open pull requests in `CurLexAI/swarms`.
3. Unchecked items in the **Repository Activation Checklist** at the bottom of this file that are not yet `VERIFIED`.
4. First failing test in `tests/` after running the suites listed under **Local Commands** plus `node --test tests/*.test.js`.
5. Documented blockers in `docs/` reports (e.g. `docs/operations/`, `docs/public-profile/`) that explicitly request follow-up.

If none of these surface a concrete unit of work, stop and report back rather than inventing one. Producing no change is a valid outcome.

---

## Agent Tooling

Two private coding agents are defined for Modal deployment.

| Agent | Model | Role | Runtime |
|---|---|---|---|
| Mihwar (المحور) | DeepSeek-Coder-V2-Instruct | Architect and generator | Modal + vLLM |
| Bayyinah (البيّنة) | Qwen2.5-Coder-32B-Instruct | Reviewer and validator | Modal + vLLM |

Configuration lives in `.agents/config/agents.yaml`.
Deployment lives in `.agents/modal_app.py`.
PR orchestration lives in `.agents/pr_review.py` and `.github/workflows/agent-review.yml`.

---

## iPhone Command Center

The iPhone is an executive control surface, not the coding runtime.

Use ChatGPT on iPhone for strategy, requirements, prompts, review, and decisions. Use SSH or GitHub from iPhone to supervise remote work running on a trusted workstation, VPS, GitHub runner, or Modal runtime.

Before any remote operation, run:

```bash
git remote -v
git status --short
git branch --show-current
```

Then apply `.agents/skills/iphone-command-center.md`.

---

## Local Commands

```bash
# Validate agent repository assets without external services
python .agents/validate.py

# Syntax-check Python agent files
python -m py_compile .agents/*.py

# Show configured agents
python .agents/invoke.py info

# Generate with Mihwar after Modal setup
python .agents/invoke.py mihwar "Describe the task"

# Review current diff with Bayyinah after Modal setup
python .agents/invoke.py bayyinah --diff

# Deploy Modal agents after secrets are configured
modal deploy .agents/modal_app.py
```

---

## Absolute Prohibitions

1. Do not commit `.env` files or real credentials.
2. Do not print secrets, tokens, or private endpoint URLs.
3. Do not claim SAMA, PDPL, NCA, or other regulatory compliance without cited evidence.
4. Do not call external AI APIs during repository work unless explicitly authorized.
5. Do not run install scripts or dependency lifecycle scripts without dependency safety review.
6. Do not commit `node_modules`, build output, caches, or opaque generated bundles as source.
7. Do not merge a PR with unresolved `CRITICAL` or `HIGH` findings.
8. Do not use stale archive assumptions after `LexPrim-main.zip` has been removed from `main`.

---

## Report Template

Use `.agents/templates/report-template.md` for all reports. Minimum fields:

```text
VERIFIED:
CHANGED:
VALIDATION:
RISKS:
DECISION:
NEXT ACTION:
```

---

## Repository Activation Checklist

A repository activation is complete only when all applicable checks are `VERIFIED` or explicitly marked `UNVERIFIED` with a reason:

- Required agent files exist.
- Policies are separated from skills.
- Python agent files compile.
- Workflow permissions allow PR comments.
- Modal decorators match the currently supported API.
- Missing external secrets are documented instead of guessed.
- Archive recovery status reflects the actual Git state.
- iPhone command-center workflows operate only against the canonical repository and remote runtime.

---

## Cursor Cloud specific instructions

### Environment notes

- `NODE_ENV=production` is set in the Cloud VM. Use `npm ci --include=dev` (not bare `npm ci`) to ensure devDependencies (`typescript`, `tsx`, `@types/*`) are installed. Without them, `npm run check` fails at the service-divergence step and `npm test` skips the TypeScript-backed integration tests.
- The VM does not ship `python` — only `python3`. Several shell gates (e.g. `p0-security-test-gate.sh`) call `python`. The update script creates a `/usr/bin/python` → `python3` symlink; if you see `python: command not found`, run `sudo ln -sf /usr/bin/python3 /usr/bin/python`.
- `ruby` is required by `scripts/commander/agent-presence-gate.sh` for YAML parsing. It is installed in the base VM image; if missing, `sudo apt-get install -y ruby`.

### Canonical validation commands

See `CLAUDE.md` and `README.md` for the full list. The key ones:

| Check | Command | Notes |
|---|---|---|
| Aggregate gate | `npm run check` | service-divergence + unit tests + boundary + CDN SRI |
| Python tests | `python3 -m pytest -q tests/` | 171 tests; 2 skipped (missing secrets) |
| Node unit tests | `npm run test:unit` | 7 tests on `unifiedAgentAdapter` |
| Node full tests | `npm test` | Includes integration tests that need `PYTHON_BACKEND_URL` and `PYTHON_BACKEND_ALLOWED_HOSTS`; 6 integration tests will fail without those env vars — this is expected |
| Security tests | `npm run test:security` | sovereignCyberRadar (8 tests) |
| TypeScript check | `npx tsc --noEmit` | Should pass cleanly (known TS2307 blocker was resolved) |
| TypeScript build | `npm run build` | Emits `.js` next to `.ts` |
| Python validate | `python3 .agents/validate.py` | Agent asset validation |
| Agent info | `python3 .agents/invoke.py info` | Lists configured agents (no secrets needed) |
| Policy gates | `bash scripts/commander/*.sh .` | 5 shell gates; all pass with WARN for missing runtime secrets |

### Integration tests vs unit tests

`npm test` runs both unit and integration tests. The integration tests (`executeAgent.non2xx`, `nodeDispatch`) require `PYTHON_BACKEND_URL` and `PYTHON_BACKEND_ALLOWED_HOSTS` env vars. Without these, they fail with `CONFIG_NOT_FOUND`. Use `npm run test:unit` for the tests that pass without any external configuration.

### Workspace layout

Both `/agent/repos/FRONT` and `/agent/repos/swarms` contain the same codebase (different GitHub repos: `CurLexAI/FRONT` and `CurLexAI/swarms`). The canonical repo is `swarms`.
