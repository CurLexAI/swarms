import fs from "fs";
import path from "path";
import yaml from "js-yaml";
import { randomUUID } from "crypto";
import logger from "../utils/logger.js";
import { AuditService } from "./AuditService.js";
import {
  buildClientSafePythonEngineError,
  sanitizeBackendErrorForAudit,
  sanitizeBackendErrorText
} from "./unifiedAgentAdapterErrorUtils.js";

interface AgentDefinition {
  id: string;
  name: string;
  category?: string;
  role: string;
  type?: "python" | "node" | "hybrid";
  required_scope?: string;
  execution?: {
    runtime: "python" | "node" | "hybrid";
  };
  contexts?: {
    allowed: string[];
  };
  enable_reasoning?: boolean;
  capabilities?: string[];  // P0: declared agent capabilities
}

interface NormalizedAgentDefinition extends AgentDefinition {
  runtime: "python" | "node" | "hybrid";
  allowedScopes: string[];
}

type ExecuteAgentMetadata = Record<string, unknown>;

export interface ExecuteAgentPayload {
  tenant_id: string;
  input: string;
  metadata?: ExecuteAgentMetadata;
}

interface ValidationResult {
  isValid: boolean;
  reason?: string;
  safePayload?: ExecuteAgentPayload;
  unknownFields?: string[];
}

export class RegistryStartupError extends Error {
  code: "CONFIG_NOT_FOUND" | "REGISTRY_LOAD_FAILURE";
  registryPath: string;

  constructor(
    code: "CONFIG_NOT_FOUND" | "REGISTRY_LOAD_FAILURE",
    registryPath: string,
    message: string,
    cause?: unknown
  ) {
    super(message);
    this.name = "RegistryStartupError";
    this.code = code;
    this.registryPath = registryPath;
    if (cause !== undefined) {
      this.cause = cause;
    }
  }
}

const ALLOWED_PAYLOAD_FIELDS = ["tenant_id", "input", "metadata"] as const;
const MAX_TENANT_ID_LENGTH = 128;
const MAX_INPUT_LENGTH = 8000;
const DEFAULT_PYTHON_ENGINE_TIMEOUT_MS = 15000;
const CLIENT_SAFE_PYTHON_ENGINE_ERROR_PATTERN =
  /^Python engine request failed with status \d+\. Please try again later(?: \(ref: [0-9a-f]{8}\))?\.$/i;

// ── P0: Capability enforcement ─────────────────────────────────────────────
// Maps agent runtime to the required declared capability.
// Agents must declare matching capabilities in .agents/config/agents.yaml to be executed.
const RUNTIME_CAPABILITY_MAP: Readonly<Record<string, string>> = {
  python: "python_execution",
  node: "node_execution",
  hybrid: "node_execution",
} as const;

// ── P0: Backend URL allowlist ──────────────────────────────────────────────
// When PYTHON_BACKEND_ALLOWED_HOSTS is set, only those hostnames are permitted
// and HTTPS is enforced. Unset = no strict validation (dev/test only).
const ALLOWED_BACKEND_HOSTS: readonly string[] = (
  process.env.PYTHON_BACKEND_ALLOWED_HOSTS ?? ""
)
  .split(",")
  .map((h) => h.trim())
  .filter(Boolean);

// ── P0: Audit redaction ────────────────────────────────────────────────────
const AUDIT_REDACTION_VERSION = "1";
const MAX_AUDIT_STRING_LENGTH = 500;
const SENSITIVE_PATTERNS: readonly RegExp[] = [
  /Bearer\s+[\w._~+/-]+=*/gi,
  /sk-[\w]{20,}/g,
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
  /\b\d{10}\b/g,  // national IDs (10-digit)
];

function sanitizeForAudit(value: unknown): unknown {
  if (typeof value === "string") {
    let s = value;
    for (const pattern of SENSITIVE_PATTERNS) {
      s = s.replace(pattern, "[REDACTED]");
    }
    return s.length > MAX_AUDIT_STRING_LENGTH
      ? s.slice(0, MAX_AUDIT_STRING_LENGTH) + "...[truncated]"
      : s;
  }
  if (Array.isArray(value)) {
    return value.map(sanitizeForAudit);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        k,
        sanitizeForAudit(v),
      ])
    );
  }
  return value;
}

function validateBackendUrl(url: string): { valid: boolean; reason?: string } {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return { valid: false, reason: "PYTHON_BACKEND_URL is not a valid URL" };
  }

  if (ALLOWED_BACKEND_HOSTS.length > 0) {
    if (parsed.protocol !== "https:") {
      return { valid: false, reason: "PYTHON_BACKEND_URL must use HTTPS" };
    }
    if (!ALLOWED_BACKEND_HOSTS.includes(parsed.hostname)) {
      return {
        valid: false,
        reason: `PYTHON_BACKEND_URL hostname not in allowlist`,
      };
    }
  }

  return { valid: true };
}

function getPythonEngineTimeoutMs() {
  const rawTimeout = process.env.UNIFIED_AGENT_PYTHON_TIMEOUT_MS;
  const parsedTimeout = Number(rawTimeout);

  if (!rawTimeout || !Number.isFinite(parsedTimeout) || parsedTimeout <= 0) {
    return DEFAULT_PYTHON_ENGINE_TIMEOUT_MS;
  }

  return Math.floor(parsedTimeout);
}

export class PythonEngineTimeoutError extends Error {
  code = "PYTHON_ENGINE_TIMEOUT" as const;
  classification = "TIMEOUT" as const;
  timeoutMs: number;
  agentId: string;

  constructor(agentId: string, timeoutMs: number, cause?: unknown) {
    super(`Python engine timed out after ${timeoutMs}ms for agent ${agentId}`);
    this.name = "PythonEngineTimeoutError";
    this.timeoutMs = timeoutMs;
    this.agentId = agentId;
    if (cause !== undefined) {
      this.cause = cause;
    }
  }
}

type BlockerStatus =
  | "AUTH_MISSING"
  | "AUTH_INVALID"
  | "AUTH_EXPIRED"
  | "CONFIG_NOT_FOUND"
  | "SYNTAX_FAILURE"
  | "TYPE_FAILURE"
  | "TEST_FAILURE"
  | "PYTHON_ENGINE_TIMEOUT"
  | "RUNTIME_FAILURE"
  | "WORKFLOW_CONFLICT"
  | "HOT_SURFACE_CONFLICT"
  | "SECRET_MISSING"
  | "DEPLOYMENT_BLOCKED"
  | "UNVERIFIED_RUNTIME";

function classifyBlocker(error: unknown): BlockerStatus {
  if (error instanceof PythonEngineTimeoutError) {
    return "PYTHON_ENGINE_TIMEOUT";
  }

  if (error instanceof Error) {
    if (error.message.includes("CONFIG_NOT_FOUND")) {
      return "CONFIG_NOT_FOUND";
    }

    if (error.message.includes("UNAUTHORIZED_SCOPE")) {
      return "AUTH_MISSING";
    }

    if (error.message.includes("AUTH_INVALID")) {
      return "AUTH_INVALID";
    }

    if (error.message.includes("AUTH_EXPIRED")) {
      return "AUTH_EXPIRED";
    }

    if (error.message.includes("SECRET_MISSING")) {
      return "SECRET_MISSING";
    }

    return "RUNTIME_FAILURE";
  }

  return "UNVERIFIED_RUNTIME";
}

export class NodeExecutionDispatchError extends Error {
  code: "CONFIG_NOT_FOUND" | "RUNTIME_FAILURE";
  classification: "CONFIG_FAILURE" | "RUNTIME_FAILURE";
  agentId: string;

  constructor(
    agentId: string,
    code: "CONFIG_NOT_FOUND" | "RUNTIME_FAILURE",
    message: string,
    cause?: unknown
  ) {
    super(message);
    this.name = "NodeExecutionDispatchError";
    this.agentId = agentId;
    this.code = code;
    this.classification = code === "CONFIG_NOT_FOUND" ? "CONFIG_FAILURE" : "RUNTIME_FAILURE";
    if (cause !== undefined) {
      this.cause = cause;
    }
  }
}

export class UnifiedAgentAdapter {
  private registryPath: string;
  private fallbackRegistryPath: string;
  private agents: Map<string, NormalizedAgentDefinition> = new Map();
  private registryStartupError: RegistryStartupError | null = null;

  constructor() {
    this.registryPath = path.join(process.cwd(), ".agents/config/agents.yaml");
    this.fallbackRegistryPath = path.join(process.cwd(), "agents/registry.yaml");
    this.loadRegistry();
  }

  private loadRegistry() {
    try {
      const selectedRegistryPath = fs.existsSync(this.registryPath)
        ? this.registryPath
        : this.fallbackRegistryPath;
      const fileContents = fs.readFileSync(selectedRegistryPath, "utf8");
      const data = yaml.load(fileContents);
      let loadedAgents = 0;
      let reasoningEnabledAgents = 0;
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        throw new RegistryStartupError(
          "REGISTRY_LOAD_FAILURE",
          selectedRegistryPath,
          `REGISTRY_LOAD_FAILURE: Invalid registry schema in ${selectedRegistryPath} (expected top-level object)`
        );
      }

      if (!("agents" in data)) {
        throw new RegistryStartupError(
          "REGISTRY_LOAD_FAILURE",
          selectedRegistryPath,
          `REGISTRY_LOAD_FAILURE: Invalid registry schema in ${selectedRegistryPath} (missing agents key)`
        );
      }

      const rawAgents = (data as { agents: unknown }).agents;
      let agentsList: AgentDefinition[];
      if (Array.isArray(rawAgents)) {
        agentsList = rawAgents as AgentDefinition[];
      } else if (rawAgents && typeof rawAgents === "object") {
        agentsList = Object.entries(rawAgents as Record<string, Record<string, unknown>>).map(
          ([key, raw]) => {
            const r = raw ?? {};
            const runtime =
              ((r.execution as { runtime?: string } | undefined)?.runtime as
                | "python"
                | "node"
                | "hybrid"
                | undefined) ?? ((r.type as "python" | "node" | "hybrid" | undefined) ?? "python");
            return {
              id: (r.id as string | undefined) ?? key,
              name: (r.name as string | undefined) ?? (r.display_name as string | undefined) ?? key,
              role: (r.role as string | undefined) ?? (r.capability as string | undefined) ?? key,
              type: runtime,
              execution: { runtime },
              capabilities:
                (r.capabilities as string[] | undefined) ??
                [RUNTIME_CAPABILITY_MAP[runtime] ?? "python_execution"],
              contexts: r.contexts as { allowed: string[] } | undefined,
              required_scope: r.required_scope as string | undefined,
              enable_reasoning: r.enable_reasoning as boolean | undefined,
              category: r.category as string | undefined,
            } satisfies AgentDefinition;
          }
        );
      } else {
        throw new RegistryStartupError(
          "REGISTRY_LOAD_FAILURE",
          selectedRegistryPath,
          `REGISTRY_LOAD_FAILURE: Invalid registry schema in ${selectedRegistryPath} (agents must be array or mapping)`
        );
      }

      agentsList.forEach((agent) => {
        const runtime = agent.execution?.runtime ?? agent.type;
        if (!runtime) {
          logger.warn({ agentId: agent.id }, "Skipping agent without runtime/type");
          return;
        }

        const allowedScopes = agent.contexts?.allowed ?? (agent.required_scope ? [agent.required_scope] : []);
        this.agents.set(agent.id, {
          ...agent,
          runtime,
          allowedScopes
        });

        loadedAgents += 1;
        if (agent.enable_reasoning) {
          reasoningEnabledAgents += 1;
        }
      });
      this.registryPath = selectedRegistryPath;

      logger.info(
        {
          loadedAgents,
          reasoningEnabledAgents,
          registryPath: selectedRegistryPath
        },
        "✅ LexPrim Intelligence Matrix loaded"
      );
    } catch (e) {
      logger.error({ err: e }, "❌ Registry Integrity Breach");
      const startupError =
        e instanceof RegistryStartupError
          ? e
          : new RegistryStartupError(
            e && typeof e === "object" && "code" in e && (e as { code?: string }).code === "ENOENT"
              ? "CONFIG_NOT_FOUND"
              : "REGISTRY_LOAD_FAILURE",
            fs.existsSync(this.registryPath) ? this.registryPath : this.fallbackRegistryPath,
            e && typeof e === "object" && "code" in e && (e as { code?: string }).code === "ENOENT"
              ? `CONFIG_NOT_FOUND: Required registry file was not found at ${this.registryPath} or ${this.fallbackRegistryPath}`
              : `REGISTRY_LOAD_FAILURE: Failed to load registry from ${this.registryPath} or ${this.fallbackRegistryPath}`,
            e
          );
      this.registryStartupError = startupError;
      throw startupError;
    }
  }

  getServiceHealth() {
    if (this.registryStartupError) {
      return {
        status: "unhealthy" as const,
        reason: this.registryStartupError.code,
        message: this.registryStartupError.message,
        registryPath: this.registryStartupError.registryPath
      };
    }

    return {
      status: "healthy" as const,
      agentsLoaded: this.agents.size,
      registryPath: this.registryPath
    };
  }

  // P0: serverPrincipalTenantId must come from server-side auth context (session/JWT),
  // never from the request payload. The caller is responsible for deriving this value
  // from a trusted source before invoking executeAgent.
  async executeAgent(
    agentId: string,
    userId: string,
    payload: unknown,
    scopes: string[],
    serverPrincipalTenantId: string
  ) {
    const agent = this.agents.get(agentId);
    if (!agent) throw new Error("Agent not found");

    if (!agent.allowedScopes.some((ctx) => scopes.includes(ctx))) {
      await AuditService.logSecurityViolation(userId, agentId, "UNAUTHORIZED_SCOPE");
      throw new Error("⛔ السيادة تمنع الوصول: لا تملك الصلاحيات الكافية.");
    }

    const validation = this.validateAndSanitizePayload(payload);
    if (!validation.isValid || !validation.safePayload) {
      await AuditService.logSecurityViolation(userId, agentId, "INVALID_EXECUTE_AGENT_PAYLOAD", {
        reason: validation.reason,
        unknown_fields: validation.unknownFields
      });
      throw new Error(validation.reason ?? "Invalid execute payload");
    }

    // P0: Tenant isolation — reject if payload tenant differs from server-side principal.
    // tenant_id values are intentionally not logged to prevent cross-tenant information leakage.
    if (validation.safePayload.tenant_id !== serverPrincipalTenantId) {
      await AuditService.logSecurityViolation(userId, agentId, "CROSS_TENANT_ACCESS_DENIED", {
        redaction_version: AUDIT_REDACTION_VERSION,
      });
      throw new Error("CROSS_TENANT_ACCESS_DENIED");
    }

    // P0: Capability enforcement — scope alone is not sufficient.
    // Agent must declare the required capability for its runtime in .agents/config/agents.yaml.
    const requiredCapability = RUNTIME_CAPABILITY_MAP[agent.runtime];
    if (!agent.capabilities?.includes(requiredCapability)) {
      await AuditService.logSecurityViolation(userId, agentId, "CAPABILITY_DENIED", {
        required_capability: requiredCapability,
        agent_capabilities: agent.capabilities,
        redaction_version: AUDIT_REDACTION_VERSION,
      });
      throw new Error(`CAPABILITY_DENIED: Agent ${agentId} lacks required capability: ${requiredCapability}`);
    }

    if (
      agent.enable_reasoning &&
      !agent.capabilities?.includes("reasoning")
    ) {
      await AuditService.logSecurityViolation(userId, agentId, "CAPABILITY_DENIED", {
        required_capability: "reasoning",
        agent_capabilities: agent.capabilities,
        redaction_version: AUDIT_REDACTION_VERSION,
      });
      throw new Error(`CAPABILITY_DENIED: Agent ${agentId} lacks required capability: reasoning`);
    }

    const taskId = randomUUID();
    const safePayload = validation.safePayload;

    if (agent.enable_reasoning) {
      logger.info(`🧠 Agent [${agent.name}] is reasoning about the legal task...`);
      const plan = await this.generateExecutionPlan(agent, safePayload);
      const metadataContext = safePayload.metadata?.context;
      const currentContext =
        metadataContext && typeof metadataContext === "object" && !Array.isArray(metadataContext)
          ? (metadataContext as Record<string, unknown>)
          : {};

      safePayload.metadata = {
        ...(safePayload.metadata ?? {}),
        context: {
          ...currentContext,
          execution_plan: plan
        }
      };
    }

    // P0: Audit entries sanitized before write; input body never logged.
    const action = `EXECUTE_${agent.runtime.toUpperCase()}_${agent.enable_reasoning ? "WITH" : "WITHOUT"}_REASONING`;

    await AuditService.logAction({
      tenant_id: safePayload.tenant_id,
      actor_id: userId,
      agent_id: agentId,
      action,
      payload: { taskId, reasoning_enabled: !!agent.enable_reasoning },
      redaction_version: AUDIT_REDACTION_VERSION,
    });

    try {
      const result =
        agent.runtime === "python"
          ? await this.forwardToPythonEngine(agent, safePayload, userId, taskId)
          : await this.executeNodeInternal(agent, safePayload);

      const verifiedResult = await this.verifyOutputQuality(result);

      // P0: Sanitize result before audit write — never log raw LLM output or legal text.
      await AuditService.updateTaskStatus(taskId, "COMPLETED", sanitizeForAudit(verifiedResult));

      return { taskId, status: "success", data: verifiedResult };
    } catch (error) {
      const blocker = classifyBlocker(error);
      logger.error({ err: error, agentId }, `💥 Intelligence Failure at Agent ${agentId}`);
      await AuditService.updateTaskStatus(taskId, "FAILED", {
        error: error instanceof Error ? sanitizeForAudit(error.message) : "Unknown error",
        blocker
      });
      throw error;
    }
  }

  private validateAndSanitizePayload(payload: unknown): ValidationResult {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return { isValid: false, reason: "Payload must be an object" };
    }

    const rawPayload = payload as Record<string, unknown>;
    const unknownFields = Object.keys(rawPayload).filter(
      (key) => !ALLOWED_PAYLOAD_FIELDS.includes(key as (typeof ALLOWED_PAYLOAD_FIELDS)[number])
    );

    if (unknownFields.length > 0) {
      return {
        isValid: false,
        reason: "Payload contains unknown fields",
        unknownFields
      };
    }

    if (typeof rawPayload.tenant_id !== "string" || !rawPayload.tenant_id.trim()) {
      return { isValid: false, reason: "tenant_id is required and must be a non-empty string" };
    }

    if (rawPayload.tenant_id.length > MAX_TENANT_ID_LENGTH) {
      return { isValid: false, reason: `tenant_id exceeds max length (${MAX_TENANT_ID_LENGTH})` };
    }

    if (typeof rawPayload.input !== "string" || !rawPayload.input.trim()) {
      return { isValid: false, reason: "input is required and must be a non-empty string" };
    }

    if (rawPayload.input.length > MAX_INPUT_LENGTH) {
      return { isValid: false, reason: `input exceeds max length (${MAX_INPUT_LENGTH})` };
    }

    let safeMetadata: ExecuteAgentMetadata | undefined;
    if (rawPayload.metadata !== undefined) {
      if (!rawPayload.metadata || typeof rawPayload.metadata !== "object" || Array.isArray(rawPayload.metadata)) {
        return { isValid: false, reason: "metadata must be an object when provided" };
      }

      safeMetadata = rawPayload.metadata as ExecuteAgentMetadata;
    }

    return {
      isValid: true,
      safePayload: {
        tenant_id: rawPayload.tenant_id.trim(),
        input: rawPayload.input,
        ...(safeMetadata ? { metadata: safeMetadata } : {})
      }
    };
  }

  private async generateExecutionPlan(_agent: NormalizedAgentDefinition, _payload: ExecuteAgentPayload) {
    return "1. تحليل السؤال القانوني. 2. استرجاع السوابق عبر RAPTOR. 3. مطابقة المخرجات مع نظام PDPL.";
  }

  private async verifyOutputQuality(result: unknown) {
    return result;
  }

  private async forwardToPythonEngine(
    agent: NormalizedAgentDefinition,
    payload: ExecuteAgentPayload,
    userId: string,
    taskId: string
  ) {
    const validation = this.validateAndSanitizePayload(payload);
    if (!validation.isValid || !validation.safePayload) {
      await AuditService.logSecurityViolation(userId, agent.id, "INVALID_FORWARD_PAYLOAD", {
        reason: validation.reason,
        unknown_fields: validation.unknownFields
      });
      throw new Error(validation.reason ?? "Invalid payload for python forwarding");
    }

    const safeBody = {
      agent_id: agent.id,
      tenant_id: validation.safePayload.tenant_id,
      input: validation.safePayload.input,
      metadata: validation.safePayload.metadata ?? {}
    };

    const backendUrl = process.env.PYTHON_BACKEND_URL?.trim();
    if (!backendUrl) {
      logger.error(
        { agentId: agent.id, configKey: "PYTHON_BACKEND_URL" },
        "CONFIG_NOT_FOUND: PYTHON_BACKEND_URL is required for python agent forwarding"
      );
      throw new Error("CONFIG_NOT_FOUND: PYTHON_BACKEND_URL is required for python agent forwarding");
    }

    const normalizedBackendUrl = backendUrl.replace(/\/+$/, "");

    // P0: Backend URL allowlist — validate hostname and protocol when allowlist is configured.
    const urlValidation = validateBackendUrl(normalizedBackendUrl);
    if (!urlValidation.valid) {
      logger.error(
        { agentId: agent.id, reason: urlValidation.reason },
        "PYTHON_BACKEND_URL_REJECTED"
      );
      throw new Error(`CONFIG_NOT_FOUND: ${urlValidation.reason}`);
    }

    const timeoutMs = getPythonEngineTimeoutMs();
    const abortController = new AbortController();
    const timeoutHandle = setTimeout(() => {
      abortController.abort();
    }, timeoutMs);

    try {
      const response = await fetch(`${normalizedBackendUrl}/api/v1/workflow/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-request-id": randomUUID(),  // P0: request tracing
          "x-task-id": taskId,            // P0: task correlation
        },
        body: JSON.stringify(safeBody),
        signal: abortController.signal
      });

      if (!response.ok) {
        const correlationId = randomUUID().slice(0, 8);
        const errorText = await response.text();
        const sanitizedBackendError = sanitizeBackendErrorText(errorText);
        const auditErrorExcerpt = sanitizeBackendErrorForAudit(errorText);

        logger.error(
          {
            agentId: agent.id,
            backendStatus: response.status,
            correlationId,
            backendError: sanitizedBackendError
          },
          "Python engine downstream error"
        );

        await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_DOWNSTREAM_FAILURE", {
          status_code: response.status,
          correlation_id: correlationId,
          backend_error_excerpt: auditErrorExcerpt
        });

        throw new Error(buildClientSafePythonEngineError(response.status, correlationId));
      }

      // P0: Type-safe JSON parse — response.ok verified before reading body.
      const responseBody: unknown = await response.json();
      return responseBody;
    } catch (error) {
      if ((error instanceof Error && error.name === "AbortError") || abortController.signal.aborted) {
        throw new PythonEngineTimeoutError(agent.id, timeoutMs, error);
      }

      if (error instanceof Error && CLIENT_SAFE_PYTHON_ENGINE_ERROR_PATTERN.test(error.message)) {
        throw error;
      }

      const correlationId = randomUUID().slice(0, 8);
      logger.error(
        {
          err: error,
          agentId: agent.id,
          correlationId
        },
        "Python engine request failed before response"
      );

      await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_REQUEST_FAILURE", {
        correlation_id: correlationId
      });

      throw new Error(buildClientSafePythonEngineError(502, correlationId));
    } finally {
      clearTimeout(timeoutHandle);
    }
  }

  /**
   * Node/hybrid split behavior (intentional):
   * - python runtime -> Python backend forwarding path
   * - node runtime   -> canonical Node runner (runAgent)
   * - hybrid runtime -> canonical Node runner (runAgent) with validated payload passthrough
   */
  private async executeNodeInternal(agent: NormalizedAgentDefinition, payload: ExecuteAgentPayload) {
    const dispatchPayload = {
      tenant_id: payload.tenant_id,
      input: payload.input,
      metadata: payload.metadata ?? {}
    };

    try {
      const runAgent = await this.getNodeDispatcher();

      return await runAgent({
        agentId: agent.id,
        input: payload.input,
        payload: dispatchPayload,
        context: "api",
        isAdmin: true
      });
    } catch (error) {
      throw this.mapNodeExecutionError(agent.id, error);
    }
  }


  private async getNodeDispatcher() {
    const nodeRuntimeModule = await import("../runners/agentRunner.js");
    return nodeRuntimeModule.runAgent;
  }

  private mapNodeExecutionError(agentId: string, error: unknown) {
    const errorCode =
      typeof error === "object" && error !== null && "code" in error && typeof error.code === "string"
        ? error.code
        : undefined;

    if (errorCode === "MISSING_API_KEY") {
      return new NodeExecutionDispatchError(
        agentId,
        "CONFIG_NOT_FOUND",
        `CONFIG_NOT_FOUND: Node runtime configuration missing for agent ${agentId}`,
        error
      );
    }

    const message = error instanceof Error ? error.message : "Node agent execution failed";

    return new NodeExecutionDispatchError(
      agentId,
      "RUNTIME_FAILURE",
      `RUNTIME_FAILURE: Node runtime execution failed for agent ${agentId}: ${message}`,
      error
    );
  }
}

export const agentAdapter = new UnifiedAgentAdapter();
