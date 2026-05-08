import { auditLogger } from "../utils/auditLogger.js";

export type ControlRole = "Admin" | "Reviewer" | "Operator" | "ReadOnly";
export type AuthProtocol = "OIDC" | "SAML";

export interface AuthenticatedPrincipal {
  actorId: string;
  role: ControlRole;
  tenantId: string;
  mfaVerifiedAt: string;
  sessionId: string;
  ipAddress: string;
}

export interface SessionPolicy {
  idleTimeoutMinutes: number;
  absoluteTimeoutMinutes: number;
  rotateAfterMinutes: number;
  bruteForceMaxAttempts: number;
  allowedIpCidrs: string[];
}

export interface SessionState {
  createdAt: Date;
  lastActivityAt: Date;
  lastRotationAt: Date;
  failedAttempts: number;
}

export interface AuditTrailEntry {
  actor: string;
  time: string;
  action: string;
  resource: string;
  tenantId: string;
  metadata?: Record<string, unknown>;
}

const ROLE_PERMISSIONS: Readonly<Record<ControlRole, readonly string[]>> = {
  Admin: ["control:read", "control:operate", "control:review", "control:admin"],
  Reviewer: ["control:read", "control:review"],
  Operator: ["control:read", "control:operate"],
  ReadOnly: ["control:read"],
};

const DEFAULT_SESSION_POLICY: SessionPolicy = {
  idleTimeoutMinutes: 15,
  absoluteTimeoutMinutes: 480,
  rotateAfterMinutes: 30,
  bruteForceMaxAttempts: 5,
  allowedIpCidrs: ["0.0.0.0/0"],
};

export class ControlPlaneSecurityService {
  private readonly authPath = "/enterprise/control";

  getControlAuthPath(): string {
    return this.authPath;
  }

  enforceEnterpriseAuth(protocol: AuthProtocol, principal: AuthenticatedPrincipal): void {
    if (!principal.mfaVerifiedAt) {
      throw new Error("AUTH_INVALID: MFA is required for control-plane access");
    }

    if (protocol !== "OIDC" && protocol !== "SAML") {
      throw new Error("AUTH_INVALID: Unsupported enterprise SSO protocol");
    }
  }

  authorizeAction(role: ControlRole, permission: string): void {
    const effectivePermissions = new Set(ROLE_PERMISSIONS[role]);
    if (!effectivePermissions.has(permission)) {
      throw new Error("AUTH_INVALID: RBAC least-privilege policy denied action");
    }
  }

  enforceSessionHardening(state: SessionState, policy: SessionPolicy = DEFAULT_SESSION_POLICY, now = new Date()): {
    shouldRotate: boolean;
  } {
    if (state.failedAttempts >= policy.bruteForceMaxAttempts) {
      throw new Error("AUTH_EXPIRED: Brute-force threshold exceeded");
    }

    const idleMs = now.getTime() - state.lastActivityAt.getTime();
    const absoluteMs = now.getTime() - state.createdAt.getTime();
    if (idleMs > policy.idleTimeoutMinutes * 60_000 || absoluteMs > policy.absoluteTimeoutMinutes * 60_000) {
      throw new Error("AUTH_EXPIRED: Session timeout policy triggered");
    }

    const rotateMs = now.getTime() - state.lastRotationAt.getTime();
    return { shouldRotate: rotateMs >= policy.rotateAfterMinutes * 60_000 };
  }

  enforceIpPolicy(ipAddress: string, policy: SessionPolicy = DEFAULT_SESSION_POLICY): void {
    if (!policy.allowedIpCidrs.includes("0.0.0.0/0") && !policy.allowedIpCidrs.includes(ipAddress)) {
      throw new Error("AUTH_INVALID: IP policy denied request");
    }
  }

  async logAdminAction(entry: AuditTrailEntry): Promise<void> {
    await auditLogger.write({
      event: "control_plane_audit",
      actor: entry.actor,
      time: entry.time,
      action: entry.action,
      resource: entry.resource,
      tenant_id: entry.tenantId,
      metadata: entry.metadata ?? {},
    });
  }

  exportAuditTrail(entries: AuditTrailEntry[]): string {
    return JSON.stringify(
      entries.map((entry) => ({
        actor: entry.actor,
        time: entry.time,
        action: entry.action,
        resource: entry.resource,
        tenantId: entry.tenantId,
        metadata: entry.metadata ?? {},
      })),
      null,
      2
    );
  }
}

export const controlPlaneSecurityService = new ControlPlaneSecurityService();
