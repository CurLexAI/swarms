# Codex Code Review in GitHub

This runbook documents how to request and operate Codex pull-request code review for this repository.

## Scope

Use this process for high-signal review focused on severe issues in GitHub pull requests.

## Preconditions

1. Codex Cloud is configured for the target repository.
2. You have access to Codex code-review settings.
3. `AGENTS.md` exists so Codex can apply repository review guidance.

## Enable Code Review

1. Configure Codex Cloud for the repository.
2. Open Codex settings: `https://chatgpt.com/codex/settings/code-review`.
3. Turn on **Code review**.

## Trigger a Review

1. In a PR comment, post: `@codex review`.
2. Wait for Codex reaction (`👀`) and posted review.

Codex posts GitHub-native review feedback and focuses review comments on high-priority risks.

## Enable Automatic Reviews

To review every new PR automatically:

1. Open code-review settings.
2. Enable **Automatic reviews**.

Codex then posts a review when a new pull request is opened for review, without requiring a manual trigger comment.

## Customize Review Focus

Codex reads `AGENTS.md` files and applies the closest guidance for files in scope.

Example section to add in `AGENTS.md`:

```md
## Review guidelines

- Do not log PII.
- Verify authentication middleware protects every route.
```

For one-off focus, add direction in the PR comment:

- `@codex review for security regressions`
- `@codex review for adapter/workflow contract risks`

## Act on Findings

After Codex posts review findings, ask Codex to fix a finding in the same PR:

```md
@codex fix the P1 issue
```

Codex runs a cloud task with PR context and can push a fix to the branch when permissions allow.

## Use `@codex` for Non-Review Tasks

If the mention is not `review`, Codex starts a cloud task using PR context.

Example:

```md
@codex fix the CI failures
```

## Troubleshooting

If Codex does not react or post a review, validate these items in order:

1. Code review is enabled in settings.
2. Codex Cloud is configured for the repository.
3. The exact trigger `@codex review` was used in a PR comment.
4. If using automatic reviews, automatic mode is enabled and the PR event matches configured triggers.

## Evidence Policy for This Repository

When reporting review operations in this repository, classify claims with exactly one label per material statement:

- `VERIFIED`
- `INFERRED`
- `UNVERIFIED`

Do not report an issue as fixed without direct runtime/path evidence.
