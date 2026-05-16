import { err, ok, type Result } from '../core/result.ts';
import {
  defaultModelForTask,
  type QararSwarmsRequest,
  type QararSwarmsResponse,
  type QararSwarmsValidationError,
  type SovereignTaskType,
  type SwarmsArchitecture
} from './sovereign-swarms-contract.ts';
import {
  QararSovereignClient,
  type QararSwarmsClientError
} from './qarar-sovereign-client.ts';
import type { BayyinahDataContext } from '../contracts/data-classification.ts';

export interface QararToolTemplate {
  readonly name: string;
  readonly description: string;
  readonly agentId: string;
  readonly taskType: SovereignTaskType;
  readonly architecture: SwarmsArchitecture;
}

export interface QararToolRunInput {
  readonly traceId: string;
  readonly prompt: string;
  readonly context?: readonly {
    readonly key: string;
    readonly value: string;
  }[];
  readonly dataContext: BayyinahDataContext;
}

export interface QararSwarmsTool {
  readonly name: string;
  readonly description: string;
  run(
    input: QararToolRunInput
  ): Promise<Result<QararSwarmsResponse, QararSwarmsClientError | QararSwarmsValidationError>>;
}

export const createQararSwarmsTool = (
  client: QararSovereignClient,
  template: QararToolTemplate
): QararSwarmsTool => ({
  name: template.name,
  description: template.description,
  run: async (
    input: QararToolRunInput
  ): Promise<Result<QararSwarmsResponse, QararSwarmsClientError | QararSwarmsValidationError>> => {
    const request: QararSwarmsRequest = {
      traceId: input.traceId,
      agentId: template.agentId,
      taskType: template.taskType,
      modelId: defaultModelForTask(template.taskType),
      architecture: template.architecture,
      prompt: input.prompt,
      context: input.context ?? [],
      dataContext: input.dataContext
    };

    const result = await client.complete(request);

    if (!result.ok) {
      return err(result.error);
    }

    return ok(result.value);
  }
});

export const createDefaultQararSwarmsTools = (
  client: QararSovereignClient
): readonly QararSwarmsTool[] => [
  createQararSwarmsTool(client, {
    name: 'qarar_legal_reasoning',
    description: 'Route complex Saudi legal reasoning through Qarar DeepSeek R1 32B.',
    agentId: 'swarms.legal-reasoning-agent',
    taskType: 'LEGAL_REASONING',
    architecture: 'DIRECT_TOOL_CALL'
  }),
  createQararSwarmsTool(client, {
    name: 'qarar_local_context',
    description: 'Route Saudi-local regulatory context lookup through Qarar ALLaM 7B.',
    agentId: 'swarms.local-context-agent',
    taskType: 'LOCAL_CONTEXT',
    architecture: 'DIRECT_TOOL_CALL'
  }),
  createQararSwarmsTool(client, {
    name: 'qarar_arabic_drafting',
    description: 'Route Arabic legal drafting through Qarar Qwen 72B Arabic.',
    agentId: 'swarms.arabic-drafting-agent',
    taskType: 'ARABIC_DRAFTING',
    architecture: 'DIRECT_TOOL_CALL'
  })
];
