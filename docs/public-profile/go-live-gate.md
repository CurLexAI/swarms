# Go-Live Gate

Canonical Repository: `CurLexAI/swarms`

## Repository Rename Rule

Any repository rename invalidates old public-profile evidence until a fresh gate run is produced against the canonical repository name.

Do not accept evidence that contains:

- `CurLexAI/LexPrim`
- `LexBANK/BSM`
- `MOTEB1989/LexPrim`
- `AUTH_MISSING`
- `404`
- placeholders
- PR or workflow references from a different repository

## Required Fresh Evidence

Before go-live, run:

```bash
bash scripts/commander/repo-rename-gate.sh
```

The command must produce:

- `reports/repo-rename/canonical-repo.txt`
- `reports/repo-rename/stale-references.txt`
- `reports/repo-rename/latest-main-runs.json`
- `reports/repo-rename/commander-report.md`

## Decision Rule

- `PASS`: no stale references in checked paths and canonical repository equals `CurLexAI/swarms`.
- `NO-GO`: stale repository references, missing GitHub CLI, wrong canonical repository, or failed latest-runs lookup.
- `needs verification`: external deploy hooks, GitHub connector settings, MCP settings, Render, Cloudflare, and other third-party dashboards.
