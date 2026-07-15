# Lex Sovereign Node threat model

| Threat | Control |
|---|---|
| Credential disclosure | Secrets supplied only as environment values; no secrets committed or logged. |
| Replay of node proof | Heartbeats include UTC timestamp, nonce, and a bounded TTL. |
| Registry tampering | Schema validation, restricted local state, and control-plane acceptance. |
| Over-broad tailnet access | Tag-based, port-specific grants; manually reviewed application. |
| Unsafe bootstrap | Default dry-run, fail-closed validation, explicit rollback confirmation. |
| Privilege escalation | Installers create constrained state; heartbeat service should run as a dedicated account. |

This package does not replace TPM/mTLS, centralized revocation, endpoint management, or a production secret manager; those remain control-plane responsibilities.
