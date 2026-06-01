import type {
  BayyinahDataContext,
  DataClass,
  RuntimeEnvironment
} from '../contracts/data-classification.ts';

/**
 * Providers currently referenced by Bayyinah integrations.
 */
export type LlmProvider =
  | 'modal'
  | 'anthropic'
  | 'groq'
  | 'gemini'
  | 'openai'
  | 'deepseek'
  | 'perplexity';

/**
 * Decision returned by sovereign egress policy.
 */
export interface EgressDecision {
  readonly allowed: boolean;
  readonly provider: LlmProvider;
  readonly reasonCode:
    | 'ALLOW_NON_PRODUCTION'
    | 'ALLOW_SOVEREIGN_PROVIDER'
    | 'BLOCK_NON_SOVEREIGN_PROVIDER'
    | 'BLOCK_REGULATED_DATA'
    | 'BLOCK_CONFIDENTIAL_DATA'
    | 'BLOCK_UNKNOWN_CASE';
  readonly message: string;
}

const SOVEREIGN_PROVIDER: LlmProvider = 'modal';

/**
 * Decide whether a given provider call is allowed under KSA sovereignty controls.
 */
export const decideEgress = (
  context: BayyinahDataContext,
  provider: LlmProvider
): EgressDecision => {
  const environment: RuntimeEnvironment = context.environment;
  const dataClass: DataClass = context.dataClass;

  if (environment !== 'production') {
    return {
      allowed: true,
      provider,
      reasonCode: 'ALLOW_NON_PRODUCTION',
      message: 'Non-production environment permits controlled provider testing.'
    };
  }

  if (provider === SOVEREIGN_PROVIDER) {
    return {
      allowed: true,
      provider,
      reasonCode: 'ALLOW_SOVEREIGN_PROVIDER',
      message: 'Provider is approved for sovereign production execution.'
    };
  }

  if (dataClass === 'REGULATED') {
    return {
      allowed: false,
      provider,
      reasonCode: 'BLOCK_REGULATED_DATA',
      message:
        'Regulated production data must not egress to non-sovereign providers.'
    };
  }

  if (dataClass === 'CONFIDENTIAL' || context.containsPII) {
    return {
      allowed: false,
      provider,
      reasonCode: 'BLOCK_CONFIDENTIAL_DATA',
      message:
        'Confidential or PII-bearing production data must not egress to non-sovereign providers.'
    };
  }

  return {
    allowed: false,
    provider,
    reasonCode: 'BLOCK_NON_SOVEREIGN_PROVIDER',
    message: 'Production Bayyinah calls are restricted to sovereign providers only.'
  };
};
