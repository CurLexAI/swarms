# GitHub Repository Hardening Runbook

Operational runbook for `scripts/commander/github-repo-hardening.ps1` — the
GitHub Repository Hardening Orchestrator. The script applies a baseline of
GitHub security controls (secret scanning, push protection, Dependabot
configuration, branch protection) to a CSV-driven list of repositories under a
single owner.

This runbook documents the prerequisites, the authentication paths, and the
break-glass posture. It does not claim regulatory compliance — record any such
claim only with cited evidence per `CLAUDE.md`.

## Scope and boundary

- Targets GitHub repository settings via the GitHub REST API through `gh`.
- Operates on a remote provider (GitHub), not on this repository.
- Honours ADR-0001: no product source is added; the script and runbook live
  under `scripts/commander/` and `docs/operations/` respectively.

## Required token permissions

When using a Fine-grained Personal Access Token (recommended) the token must
have, at minimum:

- Repository access: explicit list of target repositories.
- `Administration: Read and write` — for branch protection.
- `Secrets and security: Read and write` — for secret scanning + push protection.
- `Contents: Read and write` — for writing `.github/dependabot.yml`.
- `Metadata: Read` — mandatory companion permission on every fine-grained PAT.

When using `gh auth login`, log in as a user that holds at least `admin` on
each target repository. Org-level secret scanning toggles may additionally
require organization owner role depending on the GitHub plan.

## Authentication paths

### Interactive (developer workstation)

```powershell
winget install --id GitHub.cli
gh auth login   # GitHub.com → HTTPS or SSH → web browser flow
```

Verify with `gh auth status` — the script aborts if this fails.

### Non-interactive (CI / scheduled job)

Set `GH_TOKEN` for the current session only; never commit it, never write it
into a file or shell history.

```powershell
$env:GH_TOKEN = (Read-Host -AsSecureString "GH_TOKEN" |
                  ForEach-Object { [System.Net.NetworkCredential]::new('', $_).Password })
try {
    .\scripts\commander\github-repo-hardening.ps1 `
        -InputCsv .\repos.csv -Owner CurLexAI -DryRun
} finally {
    Remove-Item Env:\GH_TOKEN -ErrorAction SilentlyContinue
}
```

For organization-wide automation prefer a **GitHub App** with installation
access tokens (10 minute lifetime). This drops the blast radius of a leaked
credential by orders of magnitude relative to long-lived PATs.

## Input file format

A CSV with at least one header column named `RepoName`. Each row is one
repository under `-Owner`. Names are validated against
`^[A-Za-z0-9._-]{1,100}$`; invalid rows are skipped with a warning.

```csv
RepoName
bayyinah-validation
mihwar-orchestrator
qarar-engine
```

## Recommended execution order

1. Run on a **single non-production test repo** first:
   ```powershell
   .\scripts\commander\github-repo-hardening.ps1 `
       -InputCsv .\test-repo.csv -Owner CurLexAI -DryRun -Force
   ```
2. Re-run without `-DryRun` against the same single repo and inspect the API:
   ```powershell
   gh api repos/CurLexAI/<repo> --jq .security_and_analysis
   gh api repos/CurLexAI/<repo>/branches/main/protection --jq '.required_pull_request_reviews,.enforce_admins'
   ```
3. Only then expand the CSV to the broader cohort.

## Switches

| Switch | Purpose |
| --- | --- |
| `-DryRun` | Performs all preflight checks and writes the report with `DryRun` states. Makes no PATCH/PUT calls. |
| `-AllowAdminBypass` | Sets `enforce_admins=false` on the protected branch — break-glass posture. Documented exception only. |
| `-Force` | Overwrites an existing audit report without prompting. |
| `-WhatIf` / `-Confirm` | Standard PowerShell `ShouldProcess` semantics. Use `-WhatIf` for an unobtrusive plan view. |

## Audit report

The output CSV records per-repository state for each control and any error
notes. Status values are exact:

- `Success` — API call returned 2xx.
- `Success(Created)` / `Success(Updated)` — Dependabot file creation vs update.
- `Failed` — API call returned non-zero exit; `Notes` carries the trimmed
  stderr text and exit code.
- `DryRun` / `DryRun(WouldCreate)` / `DryRun(WouldUpdate)` — no mutation attempted.
- `NotAttempted` — the step was skipped (e.g. `ShouldProcess` declined).

`TimestampUtc` is ISO-8601 UTC to keep audit trails consistent across regions.

## Break-glass policy

The default posture enables `enforce_admins=true` and
`required_linear_history=true`. If an emergency hotfix must bypass the
reviewer requirement:

1. Document the incident reference and approver.
2. Run the script with `-AllowAdminBypass` against only the affected repo.
3. Within 24 hours, re-run **without** `-AllowAdminBypass` to restore the
   default posture.
4. File the incident timestamp in the relevant execution-verdict note under
   `docs/operations/`.

## What this runbook does NOT cover

- The script makes no claim about SAMA / PDPL / NCA compliance. Any such
  attestation requires separate evidence collection per `CLAUDE.md`.
- It does not enrol repositories in GitHub Advanced Security; that requires
  organization-level licensing.
- It does not verify human-side controls (2FA enforcement, SSO). Pair with an
  org-level `gh api` query before relying on the output as a holistic audit.
