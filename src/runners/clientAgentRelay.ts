export interface AgentRelayRequest {
  agent_id: string;
  tenant_id: string;
  input: unknown;
  metadata?: Record<string, unknown>;
}

export async function callLocalAgentRelay(payload: AgentRelayRequest): Promise<unknown> {
  const response = await fetch('/api/agent-relay', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`RUNTIME_FAILURE: local relay returned ${response.status}`);
  }

  return response.json();
}
