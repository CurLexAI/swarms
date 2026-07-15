# Lex Sovereign Node onboarding

1. Copy the registry example and assign a stable approved node ID.
2. Validate it: `python scripts/lex-node/verify_registry.py <registry>`.
3. Apply the installer only after reviewing its dry run.
4. Set distinct attestation and heartbeat secrets in the process environment.
5. Generate a signed attestation and heartbeat; deliver them only to the approved control plane over the private network.
6. Mark the registry active only after control-plane acceptance.

No script in this package enrolls a tailnet, changes routing, contacts a public IP service, or transmits credentials.
