# Quicknode Integration Boundary

## Status

Quicknode support is **disabled by default**. This repository contains only the boundary documentation, placeholder configuration names, and a dedicated Web3 RPC port. No live Quicknode endpoint, account token, or RPC URL is committed here.

## Supported use cases

Future Quicknode use is limited to low-sensitivity Web3 operations that can pass data-classification review:

- Read-only chain state lookups for public blockchain data.
- Transaction receipt and block metadata retrieval for operator-approved chain IDs.
- Wallet-independent event indexing for public smart-contract events.
- Health checks that prove provider reachability without sending tenant, device, legal, or regulated personal data.

Write operations, wallet signing, custody flows, transaction submission, and any use involving private keys are out of scope until a separate architecture and security review approves them.

## Data-sensitivity restrictions

Do not send any of the following to Quicknode or any other external RPC provider:

- Saudi PDPL-regulated personal data, national IDs, phone numbers, email addresses, or device identifiers.
- Tenant secrets, HMAC keys, mTLS material, API tokens, private endpoint URLs, or provider credentials.
- Internal policy documents, legal matters, source code, prompts, agent traces, or audit-ledger payloads.
- Raw wallet private keys, seed phrases, unsigned sensitive transaction payloads, or custody material.

All outbound Web3 payloads must be classified before dispatch. If a payload cannot be proven public and non-sensitive, it must stay inside the sovereign control environment.

## Configuration boundary

Use only placeholder names in source control:

- `QUICKNODE_ENABLED` — must remain `false` unless an operator explicitly enables the integration.
- `QUICKNODE_RPC_URL` — must be configured only in an approved secret store.
- `QUICKNODE_NETWORK` — optional public network label used for routing decisions.
- `QUICKNODE_CHAIN_ID` — optional numeric chain ID allowlist value.

Never commit real Quicknode RPC URLs. Quicknode URLs often embed provider tokens in the host, path, or query string, so they must be treated as secrets even when they look like ordinary HTTPS URLs.

## Hexagonal access rule

Business logic must not call Quicknode, `fetch`, WebSocket, or JSON-RPC endpoints directly. Future Web3 access must depend on the dedicated port in `src/ports/quicknodeRpcPort.ts` and receive the concrete adapter through dependency injection.

The current port factory intentionally returns a disabled adapter even when `QUICKNODE_ENABLED=true`, because no reviewed live adapter exists yet. A future live adapter must add tests proving:

1. The adapter is constructed only from secret-store configuration.
2. RPC URLs are redacted before logging, errors, and audit records.
3. Only approved chain IDs and read-only methods are allowed by policy.
4. No business-service module imports a provider SDK or performs direct RPC I/O.

## Logging rule

Logs may include the provider name, enablement state, and sanitized network label. Logs must not include full RPC URLs, host tokens, query tokens, username/password credentials, or request payloads containing tenant or device data.
