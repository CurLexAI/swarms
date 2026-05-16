/**
 * Traceable evidence reference attached to every high-value Bayyinah output.
 */
export interface SourceReference {
  readonly sourceId: string;
  readonly sourceType: 'POLICY' | 'REGULATION' | 'CASE' | 'INTERNAL_MEMO';
  readonly hash: string;
}

/**
 * Contract enforced on outputs that leave Bayyinah toward Mihwar or founder surfaces.
 */
export interface SovereignOutput<T> {
  readonly data: T;
  readonly traceId: string;
  readonly confidence: number;
  readonly sources: readonly SourceReference[];
  readonly escalated: boolean;
  readonly escalationReason: 'CONFIDENCE_BELOW_THRESHOLD' | 'NO_SOURCES' | null;
}

/**
 * Minimum confidence for autonomous downstream handling.
 */
export const MIN_AUTONOMOUS_CONFIDENCE = 0.75;

/**
 * Enforce the output contract and automatic escalation rules.
 */
export const enforceSovereignOutput = <T>(
  input: Omit<SovereignOutput<T>, 'escalated' | 'escalationReason'>
): SovereignOutput<T> => {
  if (input.traceId.trim().length === 0) {
    throw new Error('traceId must not be empty.');
  }

  if (input.confidence < 0 || input.confidence > 1) {
    throw new Error('confidence must be between 0 and 1.');
  }

  if (input.sources.length === 0) {
    return {
      ...input,
      escalated: true,
      escalationReason: 'NO_SOURCES'
    };
  }

  if (input.confidence < MIN_AUTONOMOUS_CONFIDENCE) {
    return {
      ...input,
      escalated: true,
      escalationReason: 'CONFIDENCE_BELOW_THRESHOLD'
    };
  }

  return {
    ...input,
    escalated: false,
    escalationReason: null
  };
};
