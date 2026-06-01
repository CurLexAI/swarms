# Secret Scan Summary — 2026-06-01

This summary intentionally excludes raw secret values, raw matches, endpoint URLs, and scanner payload fields.

## Scope

- Repository: `CurLexAI/swarms` local worktree at `/workspace/swarms`.
- Commit scanned: `fc38bcd2abe1de7bf60b96ae25852806effcae82`.
- Scanners: `gitleaks detect --source . --redact --report-format json --report-path gitleaks-report.json` and `trufflehog git file://. --json > trufflehog-report.json`.

## Results

- Gitleaks findings: `0`.
- TruffleHog JSON findings: `27`.
- TruffleHog verified findings: `0`.
- TruffleHog unverified findings: `27`.

## TruffleHog Detector Counts

- `Github`: `16`
- `URI`: `5`
- `Postgres`: `5`
- `CloudflareApiToken`: `1`

## TruffleHog File Counts

- `LexPrim-main.zip`: `21`
- `tests/quicknodeBoundary.test.js`: `1`
- `tests/test_qala_egress_residency_gate.py`: `1`
- `docker-compose.yml`: `1`
- `tests/sovereignCyberRadar.test.js`: `1`
- `src/security/sovereignCyberRadar.ts`: `1`
- `src/security/sovereignCyberRadar.js`: `1`

## Handling Notes

- Raw scanner outputs are local containment artifacts only and are ignored by Git because they can contain `Raw` and `RawV2` fields.
- Treat historical secret exposure as unresolved until keys are rotated/revoked by an authorized human operator.
