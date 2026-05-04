const writeRecord = (entry) => {
  console.log("[AUDIT]", JSON.stringify(entry));
};

export const auditLogger = {
  async write(entry) {
    writeRecord(entry);
  },
  writeDeferred(entry) {
    queueMicrotask(() => writeRecord(entry));
  },
};
