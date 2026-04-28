# Skill: Secure PR Review

## Purpose

Review pull requests as a security and governance auditor.
Identify risks before merge, not after.

## Trigger

Use for every PR review task. This skill defines what to check and how to report.

---

## Hard Rules

1. Default verdict is not `APPROVE`. Approval requires all checks to pass.
2. `COMMENT` is allowed for informational or low-severity findings.
3. `REQUEST_CHANGES` is required when any blocker is found.
4. Do not approve a PR that contains unresolved `CRITICAL` or `HIGH` findings.
5. Do not approve a PR that has no validation evidence.
6. Be specific — cite file paths and line numbers for every finding.

---

## Review Checklist

### 1. Secrets and Credentials

- [ ] No API keys, tokens, or passwords in diff
- [ ] No `.env` files committed (except `.env.example` with placeholders)
- [ ] No credentials hardcoded in source, tests, or config
- [ ] No secret values in commit messages

### 2. Network and External Calls

- [ ] No new outbound network calls to undocumented domains
- [ ] No `curl | bash` or equivalent patterns
- [ ] No dynamically constructed URLs containing user input
- [ ] No new webhooks or callbacks to external services

### 3. Dependencies

- [ ] `package.json` changes are intentional and justified
- [ ] Lockfile is updated consistently with `package.json`
- [ ] No unexplained major version bumps
- [ ] No dependencies removed without task justification
- [ ] No `node_modules` committed

### 4. CI/CD and Workflow Changes

- [ ] `.github/workflows/` changes are in scope of the task
- [ ] No new `permissions:` grants beyond what is needed
- [ ] No `secrets:` exposed to untrusted steps
- [ ] No `pull_request_target` used with untrusted code execution
- [ ] Third-party actions pinned to commit SHA, not a mutable tag

### 5. Unsafe Code Patterns

- [ ] No `eval()`, `new Function()`, or dynamic code execution with external input
- [ ] No SQL queries built from string concatenation with user input
- [ ] No `exec()` or `spawn()` called with user-controlled arguments
- [ ] No `innerHTML` or `dangerouslySetInnerHTML` with unsanitized content
- [ ] No path traversal patterns (`../`, `..\\`)

### 6. File System Access

- [ ] No file read/write operations on paths constructed from user input
- [ ] No access to paths outside the expected working directory

### 7. Prompt Injection Surfaces (AI-specific)

- [ ] No user input passed directly into LLM prompts without sanitization
- [ ] No external content (API responses, file contents) injected into system prompts
- [ ] No prompt templates that can be overridden by user-supplied strings
- [ ] Agent identity and instructions are not modifiable at runtime via user input

### 8. Governance

- [ ] PR description explains what changed and why
- [ ] PR is targeting the correct branch
- [ ] Validation evidence is present in PR description or linked CI run
- [ ] Changes match the stated purpose of the PR

---

## Severity Levels

| Level | Meaning | Verdict |
|---|---|---|
| `CRITICAL` | Active secret, RCE risk, or supply chain compromise | REQUEST_CHANGES — must fix before merge |
| `HIGH` | Significant security risk or governance violation | REQUEST_CHANGES — must fix before merge |
| `MEDIUM` | Risk present but not immediately exploitable | REQUEST_CHANGES or COMMENT — judgment required |
| `LOW` | Minor risk or best practice deviation | COMMENT |
| `INFO` | Observation with no security impact | COMMENT or omit |

---

## Review Report Format

```
PR:             [PR number and title]
VERDICT:        [APPROVE | REQUEST_CHANGES | COMMENT]
FINDINGS:
  - [SEVERITY] file.ts:line — description
  - [SEVERITY] file.ts:line — description
VALIDATION:     [VERIFIED — CI passed | UNVERIFIED — no evidence]
BLOCKERS:       [list of findings that must be resolved, or NONE]
```

If no findings exist:

```
FINDINGS: NONE
BLOCKERS: NONE
VERDICT:  APPROVE
```
