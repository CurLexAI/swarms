interface Logger {
  info(message: string, meta?: unknown): void;
  info(meta: Record<string, unknown>, message?: string): void;
  warn(message: string, meta?: unknown): void;
  warn(meta: Record<string, unknown>, message?: string): void;
  error(message: string, meta?: unknown): void;
  error(meta: Record<string, unknown>, message?: string): void;
}

declare const logger: Logger;
export default logger;
