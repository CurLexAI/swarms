# Supabase Optional Backend Dependency

## Purpose

Supabase is an optional backend dependency for environments that choose managed PostgreSQL, managed Auth, and SQL migration workflows. The default CurLexAI/swarms posture remains offline/no-secrets: no Supabase package, endpoint, token, migration, or runtime call is required for local agent validation.

## Responsibilities

Supabase may be used only behind server-side ports/adapters for these responsibilities:

1. **Database**
   - Store operational records in PostgreSQL when a deployment explicitly enables Supabase.
   - Keep database access behind server-side repositories or service adapters.
   - Do not allow browser/client code to run privileged SQL or call service-role APIs.

2. **Auth**
   - Validate user/session identity with public anon configuration only in browser/client code.
   - Enforce privileged authorization checks on the server before any service-role operation.
   - Treat Supabase Auth as one identity provider option, not as a replacement for mTLS, device posture, or control-plane authorization.

3. **Migrations**
   - Keep schema migrations reviewed, repeatable, and environment-scoped.
   - Run migrations only from trusted server/operator contexts.
   - Do not run migrations from browser/client bundles, public assets, or unauthenticated automation.

4. **Tenant Isolation Boundaries**
   - Model every tenant boundary explicitly in database schema, row-level security policies, and application-layer authorization.
   - Require tenant context on every server-side data operation.
   - Never trust browser-provided tenant identifiers without server-side authorization.
   - Keep cross-tenant administrative operations restricted to audited server-side workflows.

## Configuration Contract

Use `.env.example` for variable names only. Live values must be configured in the deployment secret store.

| Variable | Exposure | Required | Notes |
| --- | --- | --- | --- |
| `SUPABASE_URL` | Public/anon-safe when deployment chooses Supabase | No | Project URL. Browser/client code may read this only with anon configuration. |
| `SUPABASE_ANON_KEY` | Public/anon-safe | No | Public anon key for browser/client Auth flows and RLS-protected data paths. |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side secret-store only | No | Privileged key. Never expose to browser/client code, public assets, logs, PR comments, or static bundles. |

## Browser/Client Boundary Rule

Browser/client code may use only public anon configuration:

- Allowed in browser/client paths: `SUPABASE_URL`, `SUPABASE_ANON_KEY`.
- Forbidden in browser/client paths: `SUPABASE_SERVICE_ROLE_KEY`, service-role tokens, privileged SQL credentials, or any alias that grants bypass privileges.
- Service-role operations must be implemented in server-side adapters behind explicit Auth/database ports and dependency injection.

## Ports and Adapters Rule

If application code needs Supabase-backed database or Auth behavior, introduce ports before introducing the adapter:

- `AuthPort`: session validation, user lookup, and tenant authorization.
- `DatabasePort`: tenant-scoped read/write operations needed by the use case.
- `SupabaseAuthAdapter` and `SupabaseDatabaseAdapter`: server-side implementations only.
- Mocks/fakes: deterministic test implementations for every port.

Do not import a Supabase SDK directly into domain logic, public assets, browser bundles, or tests that should use mocks.

## Static Validation

Run the public-boundary check before committing Supabase-related changes:

```bash
npm run check:supabase-boundary
```

The check fails if service-role configuration names or service-role key patterns appear in public/client paths.
