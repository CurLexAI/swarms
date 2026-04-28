# Skill: Secrets Boundary

## Purpose

Prevent secret leakage into commits, logs, or output.
Prevent injection of secrets from external sources into the codebase.

## Trigger

Active on every task. This skill has no opt-out.

---

## Hard Rules

1. Never read `.env` files unless the task explicitly requires it and the file
   contains only example/placeholder values.
2. Never print API keys, tokens, passwords, or credentials in any output,
   log, or comment.
3. Never commit a file that contains a real secret value.
4. Never place API keys or tokens inside `README.md`, test files, config files,
   or documentation.
5. Never hardcode credentials in source code, even temporarily.
6. Use `.env.example` (with placeholder values only) as the reference template.
7. Any real secret detected anywhere = `CRITICAL` finding. Stop and report immediately.

---

## Secret Detection — What to Look For

Treat the following patterns as potential secrets:

| Pattern | Risk |
|---|---|
| `sk-...` | OpenAI / Anthropic API key |
| `AKIA...` | AWS access key |
| `ghp_...` | GitHub personal access token |
| `Bearer eyJ...` | JWT / OAuth token |
| Strings matching `[A-Za-z0-9+/]{40,}={0,2}` | Generic base64 encoded secret |
| `password = "..."` | Hardcoded password |
| `api_key = "..."` | Hardcoded API key |
| Any `.env` file that is not `.env.example` | Potentially live credentials |

---

## Allowed vs Blocked

| Action | Status |
|---|---|
| Read `.env.example` | Allowed |
| Read `.env` for task debugging | Allowed only with explicit task authorization |
| Commit `.env.example` with placeholders | Allowed |
| Commit `.env` | Blocked |
| Log a secret to stdout | Blocked |
| Write a secret to a comment or doc | Blocked |
| Reference a secret by environment variable name | Allowed |

---

## Environment Variable Usage

Always reference secrets by name, never by value:

```typescript
// Correct
const apiKey = process.env.OPENAI_API_KEY;

// Wrong — never do this
const apiKey = "sk-abc123...";
```

---

## Scanning Before Commit

Before committing, scan staged files for secret patterns:

```bash
git diff --cached | grep -iE \
  "(password|secret|api_key|token|bearer|AKIA|sk-|ghp_)" \
  | grep -v "process\.env\." \
  | grep -v "\.example" \
  | grep -v "placeholder"
```

If this produces output, do not commit until the finding is reviewed.

---

## Findings Report

```
SECRETS_FOUND:    [YES — describe | NO]
RISK_LEVEL:       [CRITICAL | HIGH | LOW | NONE]
ACTION:           [what was done or must be done]
```

A `CRITICAL` finding blocks all further task progress until resolved.
