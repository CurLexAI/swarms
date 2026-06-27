import test from "node:test";
import assert from "node:assert/strict";

test("AuditService emits strictly increasing lifecycle_seq across full lifecycle", async (t) => {
  let AuditService;
  try {
    const mod = await import("../src/services/AuditService.js");
    AuditService = mod.AuditService;
  } catch {
    t.skip("AuditService module not available for ESM import in this runtime");
    return;
  }

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

  for (const seq of seqs) {
    assert.ok(typeof seq === "number", `lifecycle_seq must be a number, got ${typeof seq}`);
  }

  for (let i = 1; i < seqs.length; i++) {
    assert.ok(
      seqs[i] > seqs[i - 1],
      `lifecycle_seq must strictly increase: got ${seqs[i - 1]} then ${seqs[i]}`
    );
  }

  assert.equal(initEvents[0].lifecycle_seq, 0);
  assert.equal(statusEvents[0].lifecycle_seq, 1);
  assert.equal(statusEvents[1].lifecycle_seq, 2);
});
