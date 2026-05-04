import { auditLogger } from "../utils/auditLogger.js";

export class AuditService {
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
    auditLogger.writeDeferred({
      event: "agent_task_status",
      taskId,
      status,
      result,
    });
  }
}
