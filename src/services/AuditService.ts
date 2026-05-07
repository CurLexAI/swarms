import { auditLogger } from "../utils/auditLogger.js";

export class AuditService {
  private static readonly TASK_STATUS_TRANSITIONS: Record<string, ReadonlySet<string>> = {
    STARTED: new Set(["COMPLETED", "FAILED"]),
  };

  private static readonly taskStatusStore = new Map<string, string>();

  static async logSecurityViolation(userId: string, agentId: string, reason: string, details: Record<string, unknown> = {}) {
    await auditLogger.write({
      event: "security",
      severity: "high",
      action: "SECURITY_VIOLATION",
      user: userId,
      details: {
        agent_id: agentId,
        reason,
        ...details,
      }
    });
  }

  static async logAction(entry: Record<string, unknown>) {
    auditLogger.writeDeferred({
      event: "agent_action",
      ...entry
    });
  }

  static async updateTaskStatus(taskId: string, status: string, result?: unknown) {
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
      result
    });
  }

  static async createTask(entry: {
    taskId: string;
    tenant_id: string;
    actor_id: string;
    agent_id: string;
    metadata?: Record<string, unknown>;
  }) {
    AuditService.taskStatusStore.set(entry.taskId, "STARTED");
    auditLogger.writeDeferred({
      event: "agent_task_init",
      status: "STARTED",
      timestamp: new Date().toISOString(),
      ...entry,
    });
  }
}
