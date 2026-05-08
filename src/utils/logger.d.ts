type LogContext = Record<string, unknown>;

interface Logger {
  info(message: string, meta?: LogContext): void;
  info(context: LogContext, message: string): void;
  warn(message: string, meta?: LogContext): void;
  warn(context: LogContext, message: string): void;
  error(message: string, meta?: LogContext): void;
  error(context: LogContext, message: string): void;
}

declare const logger: Logger;

export default logger;
