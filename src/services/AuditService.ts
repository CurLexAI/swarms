import { auditLogger } from "../utils/auditLogger.js";

export class AuditService {
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
    auditLogger.writeDeferred({
      event: "agent_task_status",
      taskId,
      status,
      result
    });
  }
}
