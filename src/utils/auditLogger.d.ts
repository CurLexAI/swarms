export const auditLogger: {
  write(entry: unknown): Promise<void>;
  writeDeferred(entry: unknown): void;
};
