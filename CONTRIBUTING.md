# Contributing to CurLexAI Swarms

Thank you for contributing to `CurLexAI/swarms`.

## Constitutional Governance

All contributions MUST comply with the project constitution:
- [`CONSTITUTION.md`](CONSTITUTION.md)

## Contribution Flow

1. Open an issue (or reference an existing one) with scope and risk notes.
2. Create a feature branch from the latest default branch.
3. Keep changes small and bounded to one purpose.
4. Add or update tests for all behavior changes.
5. Run local validation before opening a PR.
6. Open a PR with design decision, impact analysis, and validation evidence.

## Engineering Standards

- Python: 3.11+
- Architecture: Clean + Hexagonal (Ports & Adapters)
- Dependency management: explicit dependency injection for external services
- Formatting/linting: `ruff`
- Type checking: `mypy --strict`
- Tests: `pytest` and repository policy gates

## Required Local Checks

```bash
python3 -m py_compile .agents/*.py
python3 .agents/validate.py
python3 -m pytest -q tests/
ruff check .
mypy --strict .
```

If your change affects Node/TypeScript paths, also run:

```bash
npm test
npx tsc --noEmit
```

## Pull Request Requirements

Each PR must include:
- Scope and motivation
- Design decision summary
- Layer impact summary (Device / Control / Connectivity / Decision, if applicable)
- Validation output (commands + result)
- Security considerations (secrets, data flow, mTLS boundaries)

PRs that do not include validation evidence may be rejected.

## Security and Data Handling

- Never commit credentials, tokens, private keys, or `.env` values.
- Use environment variables and approved secret managers.
- Avoid logging sensitive payloads.
- Follow [`SECURITY.md`](SECURITY.md) for vulnerability reporting.

## Code of Change Discipline

- Prefer minimal, reversible, well-tested changes.
- Do not mix unrelated refactors with functional changes.
- Keep architecture boundaries intact.
