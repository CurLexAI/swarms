# SR.BSM Dashboard BFF Correction Report — 2026-05-29

## Execution Verdict

- Status: `BLOCKED` for direct SR.BSM source modification; `PARTIALLY_APPLIED` for this CurLexAI/swarms evidence and handoff update.
- Scope: Correct the prior PR by separating source-level implementation guidance from what was actually verified in this repository and on public SR.BSM surfaces.
- Canonical Path: Browser Dashboard -> SR.BSM Next.js BFF (`/api/agents`) -> Qarar Security Gate / Mihwar Gateway -> Modal vLLM backend.
- Files Touched: `docs/operations/sr-bsm-dashboard-bff-handoff-2026-05-29.md`.
- Blockers: `AUTH_MISSING` for `moteb1989/SR.BSM` source access; `/workspace/swarms` does not contain `src/components/SwarmsDashboard.tsx` or `src/app/api/agents/route.ts`.
- Hot Surface Risk: SR.BSM dashboard hooks, `/api/agents`, CSP, Render runtime auth, and gateway credentials are hot surfaces.
- What Was Actually Changed: This report now records public runtime evidence and a bounded implementation contract instead of implying that SR.BSM source was changed from the swarms worktree.
- What Was Actually Verified: Public read-only probes reached `https://www.lexprim.com`, `https://lexprim.com`, `https://sr-bsm.onrender.com`, and `https://sr-bsm.onrender.com/api/agents`.
- What Remains Unverified: SR.BSM repository source, SR.BSM lint, TypeScript, build output, gateway secret configuration, and Modal backend health.
- Next Valid Action: Apply the source patch inside SR.BSM with repository access, then run `npm run lint`, `npx tsc --noEmit`, and `npm run build` in SR.BSM.

## Evidence Labels

- `VERIFIED`: Confirmed by local repository inspection or read-only public HTTP response headers/body.
- `INFERRED`: Reasonable conclusion from verified evidence but not directly proven from source.
- `UNVERIFIED`: Not checked because source access, secrets, private runtime, or authenticated deployment access is missing.

## Public Surface Findings

| Claim | Label | Evidence |
|---|---:|---|
| `https://www.lexprim.com` serves HTTP 200 over HTTPS. | VERIFIED | `curl -I https://www.lexprim.com` returned `HTTP/1.1 200 OK`. |
| `https://lexprim.com` redirects to `https://www.lexprim.com/`. | VERIFIED | `curl -I https://lexprim.com` returned `HTTP/1.1 301 Moved Permanently` with `location: https://www.lexprim.com/`. |
| `https://sr-bsm.onrender.com` serves HTTP 200 over HTTPS. | VERIFIED | `curl -I https://sr-bsm.onrender.com` returned `HTTP/1.1 200 OK`. |
| Public unauthenticated `https://sr-bsm.onrender.com/api/agents` is protected. | VERIFIED | `curl -I https://sr-bsm.onrender.com/api/agents` returned `HTTP/1.1 401 Unauthorized`; body was `{"error":"Unauthorized","code":"UNAUTHORIZED"}`. |
| The public CSP still allows direct connections to `https://*.modal.run` and external AI APIs. | VERIFIED | The `content-security-policy` response header included `connect-src 'self' https://*.modal.run https://api.openai.com https://api.anthropic.com https://api.perplexity.ai https://api.groq.com`. |
| The deployed `/api/agents` implementation is the desired BFF contract. | UNVERIFIED | Source access is missing and the public unauthenticated route currently returns 401. |

## Public Surface Verdict

`HOLD` for security hardening before claiming the dashboard path is fully sovereign.

Reasons:

1. `VERIFIED`: The public CSP allows browser `connect-src` access to `https://*.modal.run`; this conflicts with the desired rule that the browser must not call Modal directly.
2. `VERIFIED`: The public CSP allows browser `connect-src` access to external AI API domains. That may be intentional for another feature, but it is not verified as compatible with the dashboard-only `PUBLIC` metadata flow.
3. `VERIFIED`: `/api/agents` returns 401 without browser credentials. If the dashboard is public and must display public metadata, the BFF contract needs to permit same-origin public metadata reads while keeping gateway credentials server-only. If the dashboard is authenticated, this is acceptable but must be documented in SR.BSM source and tests.

## Design Decision

Do not bypass ESLint or TypeScript as the permanent Render fix. The source-level fix belongs in `src/components/SwarmsDashboard.tsx`: define `fetchAgents` with `useCallback`, then invoke it from `useEffect` with `[fetchAgents]` as the dependency array.

Do not route the dashboard directly to Modal. The dashboard may call only same-origin `/api/agents`; that route is a server-side adapter that calls the Qarar Security Gate or Mihwar Gateway with server-only credentials and returns sanitized `PUBLIC` agent cards.

## Required SR.BSM Source Changes

### 1. Dashboard hook correction

Target file:

```text
src/components/SwarmsDashboard.tsx
```

Required implementation shape:

```tsx
const fetchAgents = useCallback(async (): Promise<void> => {
  setIsLoading(true);
  setError(null);

  try {
    const response = await fetch("/api/agents", {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch agents: ${response.status}`);
    }

    const data = (await response.json()) as AgentCard[];
    setAgents(data);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown error fetching agents";
    setError(message);
  } finally {
    setIsLoading(false);
  }
}, []);

useEffect(() => {
  void fetchAgents();
}, [fetchAgents]);
```

### 2. Server-only `/api/agents` adapter contract

Target file:

```text
src/app/api/agents/route.ts
```

Required properties:

- Use `runtime = "nodejs"` and `dynamic = "force-dynamic"`.
- Read only `QARAR_SECURITY_GATE_AGENTS_URL`, `QARAR_SECURITY_GATE_TOKEN`, and optional `QARAR_ALLOWED_ORIGIN` from `process.env`.
- Never read `NEXT_PUBLIC_*` token variables.
- Send `X-Qarar-Classification: PUBLIC` to the gateway.
- Validate the gateway payload as `unknown` before returning data.
- Drop any agent whose `classification` is not exactly `PUBLIC`.
- Return only `AgentCard[]` with `id`, `name`, `role`, `status`, `classification`, optional `model`, `capabilities`, and optional `updatedAt`.
- Return `Cache-Control: no-store`.
- Do not import a Modal SDK.
- Do not embed a Modal URL.

### 3. CSP hardening

The SR.BSM/lexprim public CSP should be tightened after confirming all frontend features that require outbound connections.

For the dashboard-only agent metadata path, the desired browser policy is:

```text
connect-src 'self'
```

If other public features require additional domains, document each exception with owner, feature, data classification, and removal criteria. Do not keep `https://*.modal.run` in browser `connect-src` for the dashboard path.

### 4. Render environment variables

Server-side only:

```text
QARAR_SECURITY_GATE_AGENTS_URL=https://<security-gate-or-mihwar-host>/v1/agents?classification=PUBLIC
QARAR_SECURITY_GATE_TOKEN=<server-only-token>
QARAR_ALLOWED_ORIGIN=https://lexprim.com
```

Forbidden for secrets:

```text
NEXT_PUBLIC_QARAR_SECURITY_GATE_TOKEN
NEXT_PUBLIC_MODAL_TOKEN
FORBIDDEN_PUBLIC_RUNTIME_TOKEN
```

## Validation Required Inside SR.BSM

Run after applying the source changes in SR.BSM:

```bash
npm run lint
npx tsc --noEmit
npm run build
```

Do not add these permanent bypasses:

```text
eslint.ignoreDuringBuilds = true
typescript.ignoreBuildErrors = true
```

## Acceptance Criteria

- `VERIFIED`: `src/components/SwarmsDashboard.tsx` imports `useCallback` and includes `fetchAgents` in the `useEffect` dependency array.
- `VERIFIED`: Browser dashboard code fetches only same-origin `/api/agents`.
- `VERIFIED`: No frontend code references Modal URLs, Modal SDKs, or agent tokens.
- `VERIFIED`: `/api/agents` filters non-`PUBLIC` records before response serialization.
- `VERIFIED`: Public CSP no longer permits `https://*.modal.run` for dashboard-origin browser connections, unless a separate documented exception exists.
- `VERIFIED`: `npm run lint`, `npx tsc --noEmit`, and `npm run build` pass inside SR.BSM.
