# Sovereign Connectivity PoC

## Run

```bash
pnpm install
pnpm test
pnpm demo
```

## Architecture
- `apps/api`: Mihwar API (`/telemetry`, `/decision`, `/devices/:id/status`).
- `packages/policy`: Deterministic Qarar policy engine.
- `apps/windows-agent`: Mock Windows cellular adapter + action executor.
- Append-only audit log with hash chaining in API and agent runtime.
