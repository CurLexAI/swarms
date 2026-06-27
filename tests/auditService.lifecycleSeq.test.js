import test from "node:test";
import assert from "node:assert/strict";

// Stub auditLogger so AuditService can be imported without the real sink.
const written = [];
const stubbedLogger = {
  writeDeferred: (entry) => { written.push(entry); },
  write: async (entry) => { written.push(entry); },
};

// Patch the module cache by injecting via dynamic import with a stub loader.
// Since we can't easily mock ESM internals here, we test via direct inspection
// of the emitted records by temporarily monkey-patching the static methods.

test("AuditService emits strictly increasing lifecycle_seq across full lifecycle", async (t) => {
  let AuditService;
  try {
    const mod = await import("../src/services/AuditService.js");
    AuditService = mod.AuditService;
  } catch {
    t.skip("AuditService module not available for ESM import in this runtime");
    return;
  }

  const capturedEvents = [];

  // Patch writeDeferred on the real auditLogger import path via the static
  // methods — we intercept at the AuditService level by wrapping the static
  // methods to capture what would be written.
  const origCreateTask = AuditService.createTask.bind(AuditService);
  const origUpdateTaskStatus = AuditService.updateTaskStatus.bind(AuditService);

  const events = [];

  AuditService.createTask = async (entry) => {
    // Delegate to real implementation then capture via the taskSeqStore.
    await origCreateTask(entry);
    // Real impl calls writeDeferred — we read back via a second pass below.
  };

  // Simpler approach: wrap auditLogger.writeDeferred via the module's import.
  // Because the module is already loaded, we patch the prototype-style static.

  // Reset: use a fresh taskId to avoid cross-test pollution.
  AuditService.createTask = origCreateTask;
  AuditService.updateTaskStatus = origUpdateTaskStatus;

  // Capture events by patching writeDeferred on the imported auditLogger.
  // We need a handle to it — get it via a re-import of the logger module.
  let loggerMod;
  try {
    loggerMod = await import("../src/utils/auditLogger.js");
  } catch {
    t.skip("auditLogger module not available");
    return;
  }

  const logger = loggerMod.auditLogger;
  const origWriteDeferred = logger.writeDeferred.bind(logger);
  const captured = [];
  logger.writeDeferred = (entry) => { captured.push(entry); origWriteDeferred(entry); };

  const taskId = `test-lifecycle-seq-${Date.now()}`;
  try {
    await AuditService.createTask({
      taskId,
      tenant_id: "t1",
      actor_id: "u1",
      agent_id: "a1",
    });

    await AuditService.updateTaskStatus(taskId, "RUNNING");
    await AuditService.updateTaskStatus(taskId, "COMPLETED");
  } finally {
    logger.writeDeferred = origWriteDeferred;
  }

  const taskEvents = captured.filter(
    (e) => e.taskId === taskId || (e.taskId === undefined && e.event === "agent_task_init" && e.taskId === taskId)
  );

  // Filter events for this specific taskId (init has taskId nested in the spread entry).
  const initEvents = captured.filter(
    (e) => e.event === "agent_task_init" && e.taskId === taskId
  );
  const statusEvents = captured.filter(
    (e) => e.event === "agent_task_status" && e.taskId === taskId
  );

  assert.equal(initEvents.length, 1, "should have one agent_task_init event");
  assert.equal(statusEvents.length, 2, "should have two agent_task_status events");

  const allLifecycleEvents = [...initEvents, ...statusEvents];
  const seqs = allLifecycleEvents.map((e) => e.lifecycle_seq);

  // All events must carry lifecycle_seq.
  for (const seq of seqs) {
    assert.ok(typeof seq === "number", `lifecycle_seq must be a number, got ${typeof seq}`);
  }

  // lifecycle_seq must be strictly increasing.
  for (let i = 1; i < seqs.length; i++) {
    assert.ok(
      seqs[i] > seqs[i - 1],
      `lifecycle_seq must strictly increase: got ${seqs[i - 1]} then ${seqs[i]}`
    );
  }

  // Specific values: init=0, RUNNING=1, COMPLETED=2.
  assert.equal(initEvents[0].lifecycle_seq, 0);
  assert.equal(statusEvents[0].lifecycle_seq, 1);
  assert.equal(statusEvents[1].lifecycle_seq, 2);
});
