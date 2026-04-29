# Policy: Network Boundary

## Purpose

Limit unauthorized outbound access, data exfiltration, prompt-injection exposure, and supply-chain risk during repository work.

---

## Default

```text
Agent internet access: OFF by default
```

Network access is allowed only when the task explicitly requires it or the command is part of a documented validation path.

---

## Allowed Without Additional Approval

| Category | Conditions |
|---|---|
| GitHub operations | Only for `CurLexAI/swarms` repository work. |
| Package registry reads | Only for install/lockfile validation. |
| Modal deployment | Only when Modal secrets are configured by the operator. |
| GitHub Actions runtime | Only repository workflows and GitHub APIs needed for PR comments/checks. |

---

## Blocked

1. Sending repository content to third-party AI APIs during repository maintenance unless explicitly authorized.
2. Downloading binaries from arbitrary URLs.
3. `curl | bash`, `wget | sh`, or equivalent install patterns.
4. Runtime callbacks or webhooks to unapproved third-party domains.
5. Dynamic outbound URLs that include repository content, file paths, tokens, or code snippets.
6. Posting raw diffs outside approved review infrastructure.

---

## Review Requirements

Flag code that:

- Constructs URLs dynamically from user input.
- Sends code, prompts, legal text, or repository data to external services.
- Includes credentials in a URL, request body, log line, or exception.
- Runs network calls during build/test without a documented fixture or mock.

---

## Report Fields

```text
NETWORK_CALLS_MADE: domains or NONE
AUTHORIZED: YES/NO/N/A
UNAUTHORIZED_CALLS: YES/NO
CODE_FINDINGS: findings or NONE
```
