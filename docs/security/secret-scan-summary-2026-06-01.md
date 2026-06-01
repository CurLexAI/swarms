# Secret Scan Summary — 2026-06-01

This summary intentionally excludes raw secret values, raw matches, endpoint URLs, and scanner payload fields.
Raw scanner reports were written only under `/tmp` during local validation and are not committed.

## Scope

- Repository: `CurLexAI/swarms` local worktree at `/workspace/swarms`.
- Commit scanned: `a137752cc1c98a8f13991beb95cbce807d17166b`.
- Gitleaks command: `/tmp/gobin/gitleaks detect --source . --redact --report-format json --report-path /tmp/gitleaks-report.json --no-banner`.
- TruffleHog command: `/tmp/trufflehog-bin/trufflehog git file:///workspace/swarms --json > /tmp/trufflehog-report.json`.

## Results

- Gitleaks findings: `0`.
- TruffleHog JSON findings: `12`.
- TruffleHog verified findings: `0`.
- TruffleHog unverified findings: `12`.

## TruffleHog Detector Counts

- `URI`: `5`
- `Postgres`: `5`
- `Github`: `1`
- `CloudflareApiToken`: `1`

## TruffleHog File Counts

- `LexPrim-main.zip`: `6`
- `tests/quicknodeBoundary.test.js`: `1`
- `tests/test_qala_egress_residency_gate.py`: `1`
- `docker-compose.yml`: `1`
- `tests/sovereignCyberRadar.test.js`: `1`
- `src/security/sovereignCyberRadar.ts`: `1`
- `src/security/sovereignCyberRadar.js`: `1`

## Handling Notes

- Raw scanner outputs are local containment artifacts only and are ignored by Git because they can contain `Raw` and `RawV2` fields.
- Verified secret count is `0`; historical unverified detector hits remain summarized without raw values.
- Treat historical secret exposure as unresolved until keys are rotated/revoked by an authorized human operator.
