---
name: lex-sovereign-node-onboarding
description: Enroll and operate a Lex Sovereign Node with offline-first, fail-closed controls.
---
# Lex Sovereign Node Onboarding

Use this skill only for approved nodes. Do not place secrets in the registry, logs, shell history, or repository.

1. Validate the registry with `scripts/lex-node/verify_registry.py`.
2. Run installers in dry-run mode first; use `--apply` only after operator approval.
3. Supply HMAC material through environment variables, never command-line arguments.
4. Generate signed attestations and heartbeats with bounded TTLs.
5. Apply Tailscale grants manually through the tailnet administration plane.
6. Roll back with the supplied rollback tool if validation or enrollment fails.

The node is not enrolled until the control plane accepts its signed heartbeat. Fail closed on identity, registry, signature, or policy errors.
