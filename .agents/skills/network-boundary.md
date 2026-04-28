# Skill: Network Boundary

## Purpose

Enforce internet access policy for all agents operating in this repository.
Reduce the attack surface for prompt injection, data exfiltration, and
unauthorized external communication.

## Trigger

Active on every task. This skill has no opt-out without explicit human authorization
documented in the task description.

---

## Default Policy

```
Agent internet access:  OFF by default
```

Agents must not initiate network requests unless the task explicitly requires it
and the request falls within the allowed categories below.

---

## Scope of This Policy

This policy governs **code-editing agents** (Codex, Claude Code, automated PR agents)
making network calls **during task execution** — i.e., while reading/writing files,
running commands, or generating code.

This policy does NOT govern:
- GitHub Actions runners calling authorized Modal endpoints (that is CI infrastructure, not agent activity)
- The Modal inference containers themselves (governed by `.agents/modal_app.py`)

---

## Allowed Network Access (for code-editing agents)

| Category | Allowed | Conditions |
|---|---|---|
| Package registry | Yes | During install only (`npm ci`, `yarn install --frozen-lockfile`, `pnpm install --frozen-lockfile`, `bun install --frozen-lockfile`) |
| Package registry domains | Yes | `registry.npmjs.org`, `registry.yarnpkg.com`, `pypi.org` only |
| HTTP methods for allowed domains | `GET` / `HEAD` only | No `POST`, `PUT`, `PATCH`, `DELETE` from agent code editing sessions |
| Git operations to `github.com` | Yes | Push/pull to `CurLexAI/swarms` only |
| Modal inference endpoints | Yes | `POST` from GitHub Actions only — `BAYYINAH_ENDPOINT`, `MIHWAR_ENDPOINT` — authenticated with `AGENT_API_TOKEN` |

---

## Blocked Network Access

The following are blocked regardless of task instructions:

| Action | Reason |
|---|---|
| Fetching external URLs in source code at build or test time | Exfiltration risk |
| Sending data to third-party APIs during development | Data leak risk |
| Calling external AI APIs (OpenAI, Anthropic, etc.) during task execution | Prompt injection risk |
| Downloading binaries from arbitrary URLs | Supply chain risk |
| `curl \| bash` or equivalent patterns | Supply chain risk |
| Webhooks or callbacks to external services | Exfiltration risk |

---

## Code Review for Network Calls

When reviewing or editing code, flag any outbound network call that:

1. Sends repository content, file paths, or code snippets to an external endpoint.
2. Uses a dynamically constructed URL where the domain is not hardcoded.
3. Includes credentials or tokens in the request body or URL.
4. Occurs outside of a clearly bounded API client with documented purpose.

Mark such findings as `NETWORK_RISK` in the task report.

---

## When External Access Is Required

If a task legitimately requires network access beyond the defaults:

1. State the specific URL and HTTP method required.
2. State the reason.
3. Wait for human confirmation before proceeding.
4. Log the request and response summary in the task report.

Example authorization in task description:

```
AUTHORIZED_NETWORK: GET https://api.example.com/v1/status — health check only
```

Without this explicit authorization, do not make the request.

---

## Findings Report

```
NETWORK_CALLS_MADE:  [list of domains contacted, or NONE]
UNAUTHORIZED_CALLS:  [YES — describe | NO]
CODE_FINDINGS:       [any network-risk patterns found in source, or NONE]
```
