export interface RunAgentInput {
  agentId: string;
  input: string;
  payload: Record<string, unknown>;
  context: string;
  isAdmin: boolean;
}

export function runAgent(input: RunAgentInput): Promise<unknown>;
