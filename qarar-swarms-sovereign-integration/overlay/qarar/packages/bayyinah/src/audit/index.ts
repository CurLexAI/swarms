export { AppendOnlyFileAuditSink } from './append-only-file-sink.ts';
export type { AppendOnlyAuditEvent, AppendOnlyAuditRecord } from './append-only-file-sink.ts';

export const safeStructuredClone = <T>(obj: T): T => {
  if (typeof globalThis.structuredClone === 'function') {
    return globalThis.structuredClone(obj);
  }

  return JSON.parse(JSON.stringify(obj)) as T;
};
