export interface AgentRelayPayload {
  agent_id: string;
  tenant_id: string;
  input: unknown;
  metadata?: Record<string, unknown>;
}

export async function relayToModal(payload: AgentRelayPayload): Promise<unknown> {
  const upstream = process.env.MODAL_RELAY_UPSTREAM_URL?.trim();
  if (!upstream) throw new Error('CONFIG_NOT_FOUND: MODAL_RELAY_UPSTREAM_URL is required');
  const endpoint = `${upstream.replace(/\/+$/, '')}/api/v1/workflow/query`;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) throw new Error(`RUNTIME_FAILURE: relay upstream returned ${response.status}`);
  return response.json();
}

export async function handleAgentRelayRequest(request: Request): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'METHOD_NOT_ALLOWED' }), { status: 405, headers: { 'content-type': 'application/json' } });
  }

  const body = await request.json() as AgentRelayPayload;
  const data = await relayToModal(body);
  return new Response(JSON.stringify(data), { status: 200, headers: { 'content-type': 'application/json' } });
}
