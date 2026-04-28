# Policy: Secrets Boundary

## Purpose

Prevent secret leakage into commits, logs, generated reports, comments, and documentation. This policy is mandatory for every task and cannot be downgraded to an optional skill.

---

## Hard Rules

1. Never commit `.env` or any file containing live credentials.
2. Never print API keys, tokens, passwords, cookies, JWTs, or private endpoint URLs.
3. Never hardcode credentials in source code, tests, docs, workflow files, or examples.
4. Use environment variable names, not values.
5. Treat every discovered real secret as `CRITICAL` and stop the task until containment is defined.
6. `.env.example` may be committed only with placeholders.
7. Generated reports must summarize secret findings without reproducing secret values.

---

## High-Risk Patterns

Flag these as potential secrets:

| Pattern | Risk |
|---|---|
| `sk-...` | LLM provider key |
| `AKIA...` | AWS access key |
| `ghp_...`, `github_pat_...` | GitHub token |
| `Bearer eyJ...` | JWT or OAuth token |
| `password = "..."` | Hardcoded password |
| `api_key = "..."` | Hardcoded API key |
| Long base64-like strings | Encoded secret candidate |
| Any non-example `.env` file | Potential live credentials |

---

## Allowed

- Referencing `process.env.SECRET_NAME`, `os.environ["SECRET_NAME"]`, or GitHub/Modal secret names.
- Committing `.env.example` with placeholder values.
- Documenting how to create secrets without exposing their values.

---

## Blocked

- Committing real secret values.
- Copying secrets into issue comments, PR bodies, Actions logs, or reports.
- Adding a workflow that echoes environment values.
- Posting a private endpoint URL together with its token.

---

## Pre-Commit Check

Run an equivalent staged diff scan before committing sensitive files:

```bash
git diff --cached | grep -iE "(password|secret|api[_-]?key|token|bearer|AKIA|sk-|ghp_|github_pat_)" || true
```

False positives are allowed only after manual review. Real matches block the commit.

---

## Report Fields

```text
SECRETS_FOUND: YES/NO
RISK_LEVEL: CRITICAL/HIGH/MEDIUM/LOW/NONE
ACTION: containment or N/A
```
