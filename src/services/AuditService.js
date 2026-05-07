import { auditLogger } from "../utils/auditLogger.js";

export class AuditService {
  static TASK_STATUS_TRANSITIONS = {
    STARTED: new Set(["COMPLETED", "FAILED"]),
  };

  static taskStatusStore = new Map();

  static async logSecurityViolation(userId, agentId, reason, details = {}) {
    await auditLogger.write({
      event: "security",
      severity: "high",
      action: "SECURITY_VIOLATION",
      user: userId,
      details: {
        agent_id: agentId,
        ...details,
        reason,
      },
    });
  }

  static async logAction(entry) {
    auditLogger.writeDeferred({
      event: "agent_action",
      ...entry,
    });
  }

  static async updateTaskStatus(taskId, status, result) {
    const currentStatus = AuditService.taskStatusStore.get(taskId);
    if (!currentStatus) {
      throw new Error(`Invalid task status transition: task ${taskId} has not been initialized`);
    }

    const allowedTransitions = AuditService.TASK_STATUS_TRANSITIONS[currentStatus];
    if (!allowedTransitions?.has(status)) {
      throw new Error(`Invalid task status transition: ${currentStatus} -> ${status}`);
    }

    AuditService.taskStatusStore.set(taskId, status);

    auditLogger.writeDeferred({
      event: "agent_task_status",
      taskId,
      status,
      result,
    });
  }

  static async createTask(entry) {
    AuditService.taskStatusStore.set(entry.taskId, "STARTED");
    auditLogger.writeDeferred({
      event: "agent_task_init",
      status: "STARTED",
      timestamp: new Date().toISOString(),
      ...entry,
    });
  }
}
