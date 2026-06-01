import {
  validateDataContext,
  type BayyinahDataContext
} from '../contracts/data-classification.ts';
import type { SourceReference } from '../contracts/sovereign-output.ts';
import { err, ok, type Result } from '../core/result.ts';

export type SovereignModelId =
  | 'deepseek-r1-32b'
  | 'allam-7b'
  | 'qwen-72b-arabic';

export type SovereignTaskType =
  | 'LEGAL_REASONING'
  | 'LOCAL_CONTEXT'
  | 'ARABIC_DRAFTING'
  | 'CONSENSUS_REVIEW';

export type SwarmsProtocol = 'ACP' | 'ANP' | 'MCP';

export type SwarmsArchitecture =
  | 'SEQUENTIAL_WORKFLOW'
  | 'HIERARCHICAL_SWARM'
  | 'DIRECT_TOOL_CALL';

export interface QararSwarmsContextItem {
  readonly key: string;
  readonly value: string;
  readonly source?: SourceReference;
}

export interface QararSwarmsRequest {
  readonly traceId: string;
  readonly agentId: string;
  readonly taskType: SovereignTaskType;
  readonly modelId: SovereignModelId;
  readonly architecture: SwarmsArchitecture;
  readonly prompt: string;
  readonly context: readonly QararSwarmsContextItem[];
  readonly dataContext: BayyinahDataContext;
  readonly preferredProtocol?: SwarmsProtocol;
}

export interface QararSwarmsResponse {
  readonly traceId: string;
  readonly agentId: string;
  readonly modelId: SovereignModelId;
  readonly protocol: SwarmsProtocol;
  readonly text: string;
  readonly confidence: number;
  readonly sources: readonly SourceReference[];
  readonly escalated: boolean;
}

export interface QararSwarmsValidationError {
  readonly code:
    | 'EMPTY_TRACE_ID'
    | 'EMPTY_AGENT_ID'
    | 'EMPTY_PROMPT'
    | 'PROMPT_TOO_LARGE'
    | 'INVALID_CONTEXT_KEY'
    | 'INVALID_DATA_CONTEXT'
    | 'MODEL_TASK_MISMATCH';
  readonly message: string;
}

const MAX_PROMPT_CHARS = 24000;

const TASK_MODEL_ALLOWLIST: ReadonlyMap<SovereignTaskType, readonly SovereignModelId[]> =
  new Map<SovereignTaskType, readonly SovereignModelId[]>([
    ['LEGAL_REASONING', ['deepseek-r1-32b']],
    ['LOCAL_CONTEXT', ['allam-7b']],
    ['ARABIC_DRAFTING', ['qwen-72b-arabic']],
    ['CONSENSUS_REVIEW', ['deepseek-r1-32b', 'allam-7b', 'qwen-72b-arabic']]
  ]);

export const validateQararSwarmsRequest = (
  request: QararSwarmsRequest
): Result<QararSwarmsRequest, QararSwarmsValidationError> => {
  if (request.traceId.trim().length === 0) {
    return err({ code: 'EMPTY_TRACE_ID', message: 'traceId must not be empty.' });
  }

  if (request.agentId.trim().length === 0) {
    return err({ code: 'EMPTY_AGENT_ID', message: 'agentId must not be empty.' });
  }

  if (request.prompt.trim().length === 0) {
    return err({ code: 'EMPTY_PROMPT', message: 'prompt must not be empty.' });
  }

  if (request.prompt.length > MAX_PROMPT_CHARS) {
    return err({
      code: 'PROMPT_TOO_LARGE',
      message: `prompt exceeds ${MAX_PROMPT_CHARS} characters.`
    });
  }

  for (const item of request.context) {
    if (!/^[a-zA-Z0-9_.:-]{1,96}$/.test(item.key)) {
      return err({
        code: 'INVALID_CONTEXT_KEY',
        message: `context key is invalid: ${item.key}`
      });
    }
  }

  try {
    validateDataContext(request.dataContext);
  } catch (error: unknown) {
    return err({
      code: 'INVALID_DATA_CONTEXT',
      message: error instanceof Error ? error.message : 'dataContext validation failed.'
    });
  }

  const allowedModels = TASK_MODEL_ALLOWLIST.get(request.taskType) ?? [];

  if (!allowedModels.includes(request.modelId)) {
    return err({
      code: 'MODEL_TASK_MISMATCH',
      message: `${request.modelId} is not approved for ${request.taskType}.`
    });
  }

  return ok(request);
};

export const defaultModelForTask = (
  taskType: SovereignTaskType
): SovereignModelId => {
  if (taskType === 'LOCAL_CONTEXT') {
    return 'allam-7b';
  }

  if (taskType === 'ARABIC_DRAFTING') {
    return 'qwen-72b-arabic';
  }

  return 'deepseek-r1-32b';
};
