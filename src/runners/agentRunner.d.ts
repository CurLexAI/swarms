export interface AgentRunnerInput {
  agentId: string;
  input: unknown;
  payload: Record<string, unknown>;
  context: string;
  isAdmin: boolean;
}

export function runAgent(input: AgentRunnerInput): Promise<unknown>;
