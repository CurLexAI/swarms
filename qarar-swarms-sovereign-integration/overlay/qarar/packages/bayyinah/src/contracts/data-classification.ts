/**
 * Data classification used before any outbound model call.
 */
export type DataClass = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'REGULATED';

/**
 * Runtime environment for Bayyinah execution.
 */
export type RuntimeEnvironment = 'development' | 'staging' | 'production';

/**
 * Jurisdiction for sovereignty enforcement.
 */
export type Jurisdiction = 'KSA';

/**
 * Minimal context required before model egress is evaluated.
 */
export interface BayyinahDataContext {
  readonly traceId: string;
  readonly jurisdiction: Jurisdiction;
  readonly environment: RuntimeEnvironment;
  readonly dataClass: DataClass;
  readonly containsPII: boolean;
}

/**
 * Validate that the data context is complete and internally consistent.
 */
export const validateDataContext = (context: BayyinahDataContext): void => {
  if (context.traceId.trim().length === 0) {
    throw new Error('traceId must not be empty.');
  }

  if (context.containsPII && context.dataClass === 'PUBLIC') {
    throw new Error('PII cannot be classified as PUBLIC.');
  }
};
