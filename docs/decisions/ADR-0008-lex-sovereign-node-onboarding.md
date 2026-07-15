# ADR-0008: Lex Sovereign Node onboarding

## Status
Accepted.

## Context
Node onboarding needs repeatable, auditable controls without silently contacting external services or embedding secrets.

## Decision
Use an offline-first registry schema, operator-applied Tailscale grants, environment-backed HMAC attestation and heartbeat proofs, dry-run installers, and explicit rollback. The control plane remains the authority for acceptance and revocation.

## Consequences
Bootstrap does not perform Tailscale login, secret provisioning, VPN enrollment, or network posting. Operators must supply approved credentials through their secret manager and apply tailnet policy separately.
