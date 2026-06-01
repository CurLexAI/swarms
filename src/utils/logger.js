const formatMessage = (value) => {
  if (typeof value === "string") {
    return value;
  }

  if (value instanceof Error) {
    return value.message;
  }

  return String(value);
};

const isStructuredMeta = (value) =>
  value !== null && typeof value === "object" && !(value instanceof Error);

const write = (level, metaOrMessage, maybeMessage) => {
  const sink = level === "error" ? console.error : console.log;
  const prefix = `[${level.toUpperCase()}]`;

  if (maybeMessage === undefined) {
    sink(`${prefix} ${formatMessage(metaOrMessage)}`);
    return;
  }

  if (isStructuredMeta(metaOrMessage)) {
    sink(`${prefix} ${formatMessage(maybeMessage)}`, metaOrMessage);
    return;
  }

  sink(`${prefix} ${formatMessage(metaOrMessage)}`, maybeMessage);
};

const logger = {
  info: (metaOrMessage, maybeMessage) =>
    write("info", metaOrMessage, maybeMessage),
  warn: (metaOrMessage, maybeMessage) =>
    write("warn", metaOrMessage, maybeMessage),
  error: (metaOrMessage, maybeMessage) =>
    write("error", metaOrMessage, maybeMessage),
};

export default logger;
