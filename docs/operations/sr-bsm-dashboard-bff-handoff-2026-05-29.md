# SR.BSM Swarms Dashboard BFF Handoff — 2026-05-29

## Execution Verdict

- Status: `BLOCKED` for direct SR.BSM source edit; `PARTIALLY_APPLIED` as a CurLexAI/swarms operational handoff.
- Scope: Fix the Render build failure in SR.BSM without permanent ESLint or TypeScript bypasses, and route dashboard agent visibility through a server-only BFF.
- Canonical Path: Browser Dashboard -> Next.js API Route / BFF in SR.BSM -> Qarar Security Gate / Mihwar Gateway -> Modal vLLM Backend.
- Files Touched: `docs/operations/sr-bsm-dashboard-bff-handoff-2026-05-29.md`.
- Blockers: `AUTH_MISSING` for direct access to `moteb1989/SR.BSM`; the target files are not present in the current `/workspace/swarms` worktree.
- Hot Surface Risk: Dashboard runtime, security gateway contract, and Render build path are hot surfaces and must be changed only in the SR.BSM repository.
- What Was Actually Changed: Added this handoff with the exact corrected implementation contract for the SR.BSM owner or agent that has repository access.
- What Was Actually Verified: The current worktree does not contain `src/components/SwarmsDashboard.tsx` or `src/app/api/agents/route.ts`.
- What Remains Unverified: SR.BSM lint, TypeScript, and build results; Qarar Security Gate runtime response shape; Render deployment status.
- Next Valid Action: Run the implementation below inside SR.BSM, then validate with `npm run lint`, `npx tsc --noEmit`, and `npm run build`.

## Design Decision

Use a narrow Next.js Backend-for-Frontend endpoint instead of exposing Modal or agent runtime credentials to the browser. The dashboard may request only `PUBLIC` agent metadata from `/api/agents`; the BFF is responsible for authenticating to `QARAR_SECURITY_GATE_AGENTS_URL` with `QARAR_SECURITY_GATE_TOKEN` from server-only environment variables.

## Layer Impact

- Browser Dashboard: Calls only local `/api/agents`; it must not know Modal URLs, Modal SDKs, or private agent tokens.
- SR.BSM BFF: Performs the server-side fetch, enforces `PUBLIC` classification, and returns sanitized cards.
- Qarar Security Gate / Mihwar Gateway: Remains the sovereign policy enforcement point before any Modal vLLM runtime.
- Modal vLLM Backend: Remains backend-only and is never called directly from frontend code.

## Required Dashboard Correction

Target file in SR.BSM:

```text
src/components/SwarmsDashboard.tsx
```

Required pattern:

```tsx
const fetchAgents = useCallback(async (): Promise<void> => {
  setIsLoading(true);
  setError(null);

  try {
    const response = await fetch("/api/agents", {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
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

Do not add permanent build bypasses:

```text
eslint.ignoreDuringBuilds = true
// or
typescript.ignoreBuildErrors = true
```

## Required Server-Only BFF Endpoint

Create this file in SR.BSM:

```text
src/app/api/agents/route.ts
```

```ts
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type AgentStatus = "online" | "offline" | "degraded" | "unknown";

type AgentCard = {
  id: string;
  name: string;
  role: string;
  status: AgentStatus;
  classification: "PUBLIC";
  model?: string;
  capabilities: string[];
  updatedAt?: string;
};

type GatewayAgent = {
  id?: unknown;
  name?: unknown;
  role?: unknown;
  status?: unknown;
  classification?: unknown;
  model?: unknown;
  capabilities?: unknown;
  updatedAt?: unknown;
};

type GatewayResponse = {
  agents?: unknown;
};

type ErrorResponse = {
  error: string;
};

function getRequiredEnv(name: string): string {
  const value = process.env[name];
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function asString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim().length > 0
    ? value
    : fallback;
}

function asStatus(value: unknown): AgentStatus {
  if (
    value === "online" ||
    value === "offline" ||
    value === "degraded" ||
    value === "unknown"
  ) {
    return value;
  }
  return "unknown";
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(
    (item): item is string => typeof item === "string" && item.trim().length > 0,
  );
}

function toPublicAgentCard(agent: GatewayAgent): AgentCard | null {
  if (agent.classification !== "PUBLIC") {
    return null;
  }

  const id = asString(agent.id, "");
  const name = asString(agent.name, "");
  if (id.length === 0 || name.length === 0) {
    return null;
  }

  const model =
    typeof agent.model === "string" && agent.model.trim().length > 0
      ? agent.model
      : undefined;
  const updatedAt =
    typeof agent.updatedAt === "string" && agent.updatedAt.trim().length > 0
      ? agent.updatedAt
      : undefined;

  return {
    id,
    name,
    role: asString(agent.role, "Sovereign agent"),
    status: asStatus(agent.status),
    classification: "PUBLIC",
    model,
    capabilities: asStringArray(agent.capabilities),
    updatedAt,
  };
}

function parseGatewayResponse(payload: GatewayResponse): AgentCard[] {
  if (!Array.isArray(payload.agents)) {
    return [];
  }

  return payload.agents
    .map((item): AgentCard | null => {
      if (typeof item !== "object" || item === null) {
        return null;
      }
      return toPublicAgentCard(item as GatewayAgent);
    })
    .filter((item): item is AgentCard => item !== null);
}

function isAllowedOrigin(request: NextRequest): boolean {
  const allowedOrigin = process.env.QARAR_ALLOWED_ORIGIN;
  const origin = request.headers.get("origin");
  if (!allowedOrigin || !origin) {
    return true;
  }
  return origin === allowedOrigin;
}

export async function GET(
  request: NextRequest,
): Promise<NextResponse<AgentCard[] | ErrorResponse>> {
  try {
    if (!isAllowedOrigin(request)) {
      return NextResponse.json({ error: "Forbidden origin" }, { status: 403 });
    }

    const gatewayUrl = getRequiredEnv("QARAR_SECURITY_GATE_AGENTS_URL");
    const gatewayToken = getRequiredEnv("QARAR_SECURITY_GATE_TOKEN");
    const response = await fetch(gatewayUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${gatewayToken}`,
        "X-Qarar-Classification": "PUBLIC",
        "X-Qarar-Client": "SR.BSM-Dashboard",
      },
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Gateway request failed with status ${response.status}` },
        { status: 502 },
      );
    }

    const payload = (await response.json()) as GatewayResponse;
    const agents = parseGatewayResponse(payload);
    return NextResponse.json(agents, {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown agents bridge error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
```

## Render Environment Variables

Configure these only as server-side secrets in Render:

```text
QARAR_SECURITY_GATE_AGENTS_URL=https://<security-gate-or-mihwar-host>/v1/agents?classification=PUBLIC
QARAR_SECURITY_GATE_TOKEN=<server-only-token>
QARAR_ALLOWED_ORIGIN=https://lexprim.com
```

Never use these client-exposed names for secrets:

```text
NEXT_PUBLIC_QARAR_SECURITY_GATE_TOKEN
NEXT_PUBLIC_MODAL_TOKEN
NEXT_PUBLIC_AGENT_API_TOKEN
```

## Validation Commands for SR.BSM

Run inside SR.BSM after applying the code change:

```bash
npm run lint
npx tsc --noEmit
npm run build
```

Expected result: all three commands pass without `eslint.ignoreDuringBuilds` or `typescript.ignoreBuildErrors`.
