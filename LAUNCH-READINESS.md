# Qarar/Bayyinah Launch Readiness

## Final Verdict

**HOLD** — documentation, local workflow hardening, and evidence scaffolding are present, but live deployment, endpoint smoke, Bayyinah blocking behavior, control-boundary runtime checks, device pilot, limited live, and full live are not verified in this environment.

## Ladder Status

| Phase | Status | Evidence | Blocker Severity |
|---|---|---|---|
| 1. Governance | VERIFIED | `LAUNCH-GOVERNANCE.md` defines data classification, approvals, rollback, kill switch, scope, incident path, and no-auto-deploy rule. | NONE |
| 2. Secrets | VERIFIED_NAME_MANIFEST_ONLY | `docs/secrets-manifest.md` lists required secret names only and fail-closed rules. Values were not inspected or printed. | HIGH until presence is verified in approved stores. |
| 3. Local gates | VERIFIED_WITH_WARNINGS | Required local commands were run; agent endpoint secrets are absent in this environment, so live runtime phases remain blocked. | HIGH for live phases until secrets/runtime are verified. |
| 4. Modal deploy | HOLD | Manual command is prepared; deployment was not executed. | HIGH until production approval and deploy evidence exist. |
| 5. Modal CLI smoke | HOLD | Must run only after approved deploy. | HIGH until Modal CLI smoke verifies import, secret access, model availability, and safe inference. |
| 6. Endpoint smoke | HOLD | Must run only after approved deploy and smoke secrets. | HIGH until authenticated success, invalid-token failure, and redacted logs are verified. |
| 7. Bayyinah PR gate | HOLD | Workflow exists, but runtime blocking conditions require live verification and branch protection evidence. | HIGH until gate is proven blocking. |
| 8. Control boundary | HOLD | Policy boundary checks require runtime/audit evidence. | HIGH until allowed/disallowed/classification decisions are audit logged. |
| 9. Device/connectivity pilot | HOLD | No pilot run executed. | HIGH until allowlisted low-risk pilot with operator and kill switch. |
| 10. Limited live | HOLD | Not eligible until phases 1-9 pass. | CRITICAL if enabled early. |
| 11. Full live | HOLD | Not eligible until all gates pass and no CRITICAL/HIGH blockers remain. | CRITICAL if marked ready from documentation-only evidence. |

## Exact Local Validation Command List

Run in strict order from the repository root:

```bash
npm ci
npm run check --if-present
npm run test --if-present
npm run build --if-present
python3 -m py_compile .agents/*.py
python3 .agents/validate.py
bash scripts/commander/agent-presence-gate.sh .
python3 scripts/security/static_audit.py .
npm run deploy:evidence:validate --if-present
```

Known repository-discovery findings:

- `src/server.js` is absent.
- `src/app.js` is absent.
- `data/agents/index.json` is absent.
- `data/agents/*.yaml` is absent.
- `backend/app/services/tree_builder.py` is absent, so the reported indentation blocker around line 131/132 is not reproducible from current repository content.

## Manual Modal Deployment Command

Do not run without production approval:

```bash
gh workflow run modal-runtime-activation.yml \
  --ref main \
  -f deploy_modal=true \
  -f run_smoke=true
```

Alternative direct Modal command after approval and validated secrets only:

```bash
modal deploy .agents/modal_app.py
```

## Command Log Summary

| Command | Result | Notes |
|---|---|---|
| `npm ci` | PASS | Installed 36 packages from lockfile; npm emitted non-blocking unknown `http-proxy` config warning. |
| `npm run check --if-present` | PASS | Aggregate gate passed, including unit tests, boundary, SRI, audit integrity, swarms presence, Supabase boundary, and runtime policy checks. |
| `npm run test --if-present` | PASS | 30 Node tests passed. |
| `npm run build --if-present` | PASS | TypeScript build completed; generated JS artifacts were removed from the commit scope. |
| `python3 -m py_compile .agents/*.py` | PASS | Python agent files compiled. |
| `python3 .agents/validate.py` | PASS | Required agent files validated. |
| `bash scripts/commander/agent-presence-gate.sh .` | PASS_WITH_WARNINGS | Agent registry parsed; Mihwar/Bayyinah present; endpoint/API-token secrets are missing in this environment, so live agents remain HOLD. |
| `python3 scripts/security/static_audit.py .` | PASS | No obvious secrets found. |
| `npm run deploy:evidence:validate --if-present` | PASS | Launch evidence schema validated with final verdict `HOLD`. |

## Blocker List by Severity

### CRITICAL

- Full-live and limited-live activation are blocked until all prior phases pass with evidence.

### HIGH

- Required secret values were not inspected and must be validated in approved secret stores by name only.
- Modal deploy was not approved or executed.
- Modal CLI smoke was not executed.
- Endpoint smoke was not executed.
- Bayyinah PR gate blocking behavior is not proven against live review outputs and branch protection.
- Control-boundary audit behavior is not proven against runtime decisions.
- Device/connectivity pilot was not executed.

### MEDIUM

- Agent presence gate warns that Bayyinah/Mihwar endpoint secrets are absent in this environment; this blocks live runtime phases but not local source validation.

### LOW

- `src/server.js`, `src/app.js`, and `data/agents/*` discovery targets are absent in the current repository layout.

## Decision

The repository remains on **HOLD**. Do not mark `READY` until live deployment and runtime smoke evidence are added without CRITICAL/HIGH blockers.
