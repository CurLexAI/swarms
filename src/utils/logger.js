const write = (level, message, meta) => {
  const sink = level === "error" ? console.error : console.log;
  if (meta === undefined) {
    sink(`[${level.toUpperCase()}] ${message}`);
    return;
  }
  sink(`[${level.toUpperCase()}] ${message}`, meta);
};

const logger = {
  info: (message, meta) => write("info", message, meta),
  warn: (message, meta) => write("warn", message, meta),
  error: (message, meta) => write("error", message, meta),
};

export default logger;
