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

interface AgentExecutionAuthorizationRequest {
  actorId: string;
  tenantId: string;
  principalTenantId: string;
  action: "execute";
  agent: NormalizedAgentDefinition;
  actorScopes: string[];
  requestedCapabilities: string[];
  scopeHierarchy?: Readonly<Record<string, readonly string[]>>;
}

interface AgentExecutionAuthorizationDecision {
  allowed: boolean;
  matchedRule: string;
  reasonCode: string;
}

interface PolicyService {
  authorizeAgentExecution(
    request: AgentExecutionAuthorizationRequest
  ): AgentExecutionAuthorizationDecision;
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
const MAX_BACKEND_ERROR_SNIPPET_LENGTH = 512;
const DEFAULT_PYTHON_ENGINE_MAX_RETRIES = 2;
const DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS = 250;
const RETRYABLE_HTTP_STATUSES = new Set([502, 503, 504]);
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
  .map((h: string) => h.trim())
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
  const rawTimeout = process.env.PYTHON_BACKEND_TIMEOUT_MS ?? process.env.UNIFIED_AGENT_PYTHON_TIMEOUT_MS;
  const parsedTimeout = Number(rawTimeout);

  if (!rawTimeout || !Number.isFinite(parsedTimeout) || parsedTimeout <= 0) {
    return DEFAULT_PYTHON_ENGINE_TIMEOUT_MS;
  }

  return Math.floor(parsedTimeout);
}

class DefaultPolicyService implements PolicyService {
  authorizeAgentExecution(
    request: AgentExecutionAuthorizationRequest
  ): AgentExecutionAuthorizationDecision {
    const { tenantId, principalTenantId, agent, actorScopes, requestedCapabilities, scopeHierarchy } = request;
    if (tenantId !== principalTenantId) return { allowed: false, matchedRule: "tenant_boundary", reasonCode: "CROSS_TENANT_ACCESS_DENIED" };

    const effectiveScopes = new Set(actorScopes);
    for (const scope of actorScopes) {
      for (const inheritedScope of scopeHierarchy?.[scope] ?? []) effectiveScopes.add(inheritedScope);
    }
    if (!agent.allowedScopes.some((scope) => effectiveScopes.has(scope))) {
      return { allowed: false, matchedRule: "allowed_scopes", reasonCode: "UNAUTHORIZED_SCOPE" };
    }

    const agentCapabilities = new Set(agent.capabilities ?? []);
    for (const requiredCapability of requestedCapabilities) {
      if (!agentCapabilities.has(requiredCapability)) {
        return { allowed: false, matchedRule: "required_capabilities", reasonCode: "CAPABILITY_DENIED" };
      }
    }

    return { allowed: true, matchedRule: "allow_agent_execution", reasonCode: "ALLOW" };
  }
}

function getPythonEngineMaxAttempts() {
  const parsed = Number(process.env.PYTHON_BACKEND_MAX_ATTEMPTS);
  if (!Number.isFinite(parsed) || parsed < 1) return DEFAULT_PYTHON_ENGINE_MAX_RETRIES;
  return Math.floor(parsed);
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableNetworkError(error: unknown) {
  if (!(error instanceof Error) || error.name === "AbortError") return false;
  const code = (error as NodeJS.ErrnoException).code;
  return code === "ECONNRESET" || code === "ETIMEDOUT" || code === "EAI_AGAIN" || code === "UND_ERR_CONNECT_TIMEOUT";
}

type RuntimeFailureClass = "RUNTIME_FAILURE" | "UNVERIFIED_RUNTIME" | "PYTHON_ENGINE_TIMEOUT";
type BlockerStatus = "AUTH_MISSING" | "AUTH_INVALID" | "AUTH_EXPIRED" | "CONFIG_NOT_FOUND" | "SYNTAX_FAILURE" | "TYPE_FAILURE" | "TEST_FAILURE" | "PYTHON_ENGINE_TIMEOUT" | "RUNTIME_FAILURE" | "WORKFLOW_CONFLICT" | "HOT_SURFACE_CONFLICT" | "SECRET_MISSING" | "DEPLOYMENT_BLOCKED" | "UNVERIFIED_RUNTIME";

class PythonEngineRuntimeError extends Error {
  code: RuntimeFailureClass;
  upstreamStatus: number | null;
  retryable: boolean;
  constructor(message: string, code: RuntimeFailureClass, upstreamStatus: number | null, retryable: boolean, cause?: unknown) {
    super(message);
    this.name = "PythonEngineRuntimeError";
    this.code = code;
    this.upstreamStatus = upstreamStatus;
    this.retryable = retryable;
    if (cause !== undefined) this.cause = cause;
  }
}

function createPythonRuntimeError(params: { code: RuntimeFailureClass; status: number | null; retryable: boolean; correlationId?: string; message?: string; cause?: unknown; }) {
  const message = params.message ?? (params.status !== null ? buildClientSafePythonEngineError(params.status, params.correlationId) : "Python engine request failed. Please try again later.");
  return new PythonEngineRuntimeError(message, params.code, params.status, params.retryable, params.cause);
}

function classifyBlocker(error: unknown): BlockerStatus {
  if (error instanceof PythonEngineRuntimeError) return error.code;
  if (error instanceof Error) {
    if (error.message.includes("CONFIG_NOT_FOUND")) return "CONFIG_NOT_FOUND";
    if (error.message.includes("UNAUTHORIZED_SCOPE")) return "AUTH_MISSING";
    if (error.message.includes("AUTH_INVALID")) return "AUTH_INVALID";
    if (error.message.includes("AUTH_EXPIRED")) return "AUTH_EXPIRED";
    if (error.message.includes("SECRET_MISSING")) return "SECRET_MISSING";
    return "RUNTIME_FAILURE";
  }
  return "UNVERIFIED_RUNTIME";
}

export class NodeExecutionDispatchError extends Error {
  code: "CONFIG_NOT_FOUND" | "RUNTIME_FAILURE";
  classification: "CONFIG_FAILURE" | "RUNTIME_FAILURE";
  agentId: string;
  constructor(agentId: string, code: "CONFIG_NOT_FOUND" | "RUNTIME_FAILURE", message: string, cause?: unknown) {
    super(message);
    this.name = "NodeExecutionDispatchError";
    this.agentId = agentId;
    this.code = code;
    this.classification = code === "CONFIG_NOT_FOUND" ? "CONFIG_FAILURE" : "RUNTIME_FAILURE";
    if (cause !== undefined) this.cause = cause;
  }
}

export class UnifiedAgentAdapter {
  private registryPath: string;
  private fallbackRegistryPath: string;
  private agents: Map<string, NormalizedAgentDefinition> = new Map();
  private registryStartupError: RegistryStartupError | null = null;
  private policyService: PolicyService;

  constructor(policyService: PolicyService = new DefaultPolicyService()) {
    this.registryPath = path.join(process.cwd(), ".agents/config/agents.yaml");
    this.fallbackRegistryPath = path.join(process.cwd(), "agents/registry.yaml");
    this.policyService = policyService;
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

    const validation = this.validateAndSanitizePayload(payload);
    if (!validation.isValid || !validation.safePayload) {
      await AuditService.logSecurityViolation(userId, agentId, "INVALID_EXECUTE_AGENT_PAYLOAD", {
        reason: validation.reason,
        unknown_fields: validation.unknownFields
      });
      throw new Error(validation.reason ?? "Invalid execute payload");
    }

    const requiredCapability = RUNTIME_CAPABILITY_MAP[agent.runtime];
    const requestedCapabilities = [requiredCapability, ...(agent.enable_reasoning ? ["reasoning"] : [])];
    const authorizationDecision = this.policyService.authorizeAgentExecution({
      actorId: userId,
      tenantId: validation.safePayload.tenant_id,
      principalTenantId: serverPrincipalTenantId,
      action: "execute",
      agent,
      actorScopes: scopes,
      requestedCapabilities
    });

    if (!authorizationDecision.allowed) {
      const auditDetails: Record<string, unknown> = {
        matched_rule: authorizationDecision.matchedRule,
        reason_code: authorizationDecision.reasonCode,
        redaction_version: AUDIT_REDACTION_VERSION
      };

      if (authorizationDecision.reasonCode === "CAPABILITY_DENIED") {
        auditDetails.required_capabilities = requestedCapabilities;
        auditDetails.agent_capabilities = agent.capabilities;
      }

      await AuditService.logSecurityViolation(userId, agentId, authorizationDecision.reasonCode, auditDetails);
      logger.warn(
        {
          actorId: userId,
          agentId,
          matchedRule: authorizationDecision.matchedRule,
          reasonCode: authorizationDecision.reasonCode
        },
        "Agent execution denied by policy evaluator"
      );

      if (authorizationDecision.reasonCode === "UNAUTHORIZED_SCOPE") {
        throw new Error("⛔ السيادة تمنع الوصول: لا تملك الصلاحيات الكافية.");
      }
      if (authorizationDecision.reasonCode === "CAPABILITY_DENIED") {
        throw new Error(`CAPABILITY_DENIED: Agent ${agentId} lacks required capability: ${requestedCapabilities.join(",")}`);
      }
      throw new Error(authorizationDecision.reasonCode);
    }

    const taskId = randomUUID();
    const safePayload = validation.safePayload;
    try {
      await AuditService.createTask({
        taskId,
        tenant_id: safePayload.tenant_id,
        actor_id: userId,
        agent_id: agentId,
        metadata: {
          runtime: agent.runtime,
          reasoning_enabled: !!agent.enable_reasoning,
          request_metadata: sanitizeForAudit(safePayload.metadata ?? {})
        }
      });
    } catch (error: unknown) {
      logger.error({ err: error, taskId, agentId }, "RUNTIME_FAILURE: audit task initialization failed");
      throw new Error(`RUNTIME_FAILURE: audit initialization failed for task ${taskId}`);
    }

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
    } catch (error: unknown) {
      const blocker = classifyBlocker(error);
      const structuredFailure = error instanceof PythonEngineRuntimeError
        ? { failure_class: error.code, upstream_status: error.upstreamStatus, retryable: error.retryable }
        : { failure_class: blocker, upstream_status: null };

      logger.error({ err: error, agentId, structuredFailure }, `💥 Intelligence Failure at Agent ${agentId}`);
      await AuditService.updateTaskStatus(taskId, "FAILED", {
        error: error instanceof Error ? sanitizeForAudit(error.message) : "Unknown error",
        blocker,
        ...structuredFailure
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
        reason: sanitizeForAudit(validation.reason),
        unknown_fields: sanitizeForAudit(validation.unknownFields)
      });
      throw new Error(validation.reason ?? "Invalid payload for python forwarding");
    }
    const safeBody = { agent_id: agent.id, tenant_id: validation.safePayload.tenant_id, input: validation.safePayload.input, metadata: validation.safePayload.metadata ?? {} };
    const backendUrl = process.env.PYTHON_BACKEND_URL?.trim();
    if (!backendUrl) {
      logger.error({ agentId: agent.id, configKey: "PYTHON_BACKEND_URL" }, "CONFIG_NOT_FOUND: PYTHON_BACKEND_URL is required for python agent forwarding");
      throw new Error("CONFIG_NOT_FOUND: PYTHON_BACKEND_URL is required for python agent forwarding");
    }
    const normalizedBackendUrl = backendUrl.replace(/\/+$/, "");
    const endpoint = `${normalizedBackendUrl}/api/v1/workflow/query`;
    const urlValidation = validateBackendUrl(normalizedBackendUrl);
    if (!urlValidation.valid) throw new Error(`CONFIG_NOT_FOUND: ${urlValidation.reason}`);

    const timeoutMs = getPythonEngineTimeoutMs();
    const maxAttempts = getPythonEngineMaxAttempts();
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const abortController = new AbortController();
      const timeoutHandle = setTimeout(() => abortController.abort(), timeoutMs);
      const requestId = randomUUID();

      try {
        const response = await fetch(`${normalizedBackendUrl}/api/v1/workflow/query`, { method: "POST", headers: { "Content-Type": "application/json", "x-request-id": requestId, "x-task-id": taskId }, body: JSON.stringify(safeBody), signal: abortController.signal });
        if (!response.ok) {
          const rawError = await response.text();
          const retryable = RETRYABLE_HTTP_STATUSES.has(response.status);
          if (retryable && attempt < maxAttempts) { await sleep(DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS * 2 ** (attempt - 1)); continue; }
          const correlationId = randomUUID().slice(0, 8);
          await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_DOWNSTREAM_FAILURE", { status_code: response.status, correlation_id: correlationId, request_id: requestId, endpoint, backend_error_excerpt: sanitizeForAudit(sanitizeBackendErrorForAudit(rawError)) });
          throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: response.status, retryable, correlationId });
        }

        const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
        if (!contentType.includes("application/json")) {
          const correlationId = randomUUID().slice(0, 8);
          const rawPayload = await response.text();
          await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_CONTENT_TYPE_MISMATCH", { status_code: response.status, content_type: contentType || "missing", correlation_id: correlationId, request_id: requestId, task_id: taskId, endpoint, backend_error_excerpt: sanitizeForAudit(sanitizeBackendErrorForAudit(rawPayload)) });
          throw createPythonRuntimeError({ code: "UNVERIFIED_RUNTIME", status: response.status, retryable: false, correlationId });
        }

        try { return await response.json(); }
        catch (parseError) {
          const correlationId = randomUUID().slice(0, 8);
          await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_JSON_PARSE_FAILURE", { status_code: response.status, correlation_id: correlationId, request_id: requestId, task_id: taskId, endpoint });
          throw createPythonRuntimeError({ code: "UNVERIFIED_RUNTIME", status: response.status, retryable: false, correlationId, cause: parseError });
        }
      } catch (error) {
        if ((error instanceof Error && error.name === "AbortError") || abortController.signal.aborted) throw createPythonRuntimeError({ code: "PYTHON_ENGINE_TIMEOUT", status: null, retryable: false, message: `Python engine timed out after ${timeoutMs}ms for agent ${agent.id}`, cause: error });
        if (error instanceof PythonEngineRuntimeError) throw error;
        if (isRetryableNetworkError(error) && attempt < maxAttempts) { await sleep(DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS * 2 ** (attempt - 1)); continue; }
        const correlationId = randomUUID().slice(0, 8);
        await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_REQUEST_FAILURE", { correlation_id: correlationId, endpoint, task_id: taskId });
        throw createPythonRuntimeError({ code: "UNVERIFIED_RUNTIME", status: 502, retryable: false, correlationId, cause: error });
      } finally { clearTimeout(timeoutHandle); }
    }
    throw createPythonRuntimeError({ code: "UNVERIFIED_RUNTIME", status: null, retryable: false, message: "Python engine exhausted retry budget" });
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
      const runAgent = await this.getNodeDispatcher(agent.id);

      return await runAgent({
        agentId: agent.id,
        input: payload.input,
        payload: dispatchPayload,
        context: "api",
        isAdmin: true
      });
    } catch (error: unknown) {
      throw this.mapNodeExecutionError(agent.id, error);
    }
  }


  private async getNodeDispatcher(agentId: string) {
    try {
      const nodeRuntimeModule = await import("../runners/agentRunner.js");
      return nodeRuntimeModule.runAgent;
    } catch (error: unknown) {
      throw this.mapNodeExecutionError(agentId, error);
    }
  }

  private isNodeRunnerModuleNotFound(error: unknown) {
    if (!(error instanceof Error)) {
      return false;
    }

    const err = error as NodeJS.ErrnoException & { url?: string };
    const message = error.message.toLowerCase();
    const missingRunnerPath = "../runners/agentrunner.js";
    const missingRunnerUrl = "/runners/agentrunner.js";

    return (
      err.code === "ERR_MODULE_NOT_FOUND" ||
      (err.code === "MODULE_NOT_FOUND" && message.includes("agentrunner.js")) ||
      (message.includes("cannot find module") && message.includes(missingRunnerPath)) ||
      (message.includes("cannot find module") && message.includes(missingRunnerUrl)) ||
      (typeof err.url === "string" && err.url.toLowerCase().includes(missingRunnerUrl))
    );
  }

  private mapNodeExecutionError(agentId: string, error: unknown) {
    const errorCode =
      typeof error === "object" && error !== null && "code" in error && typeof error.code === "string"
        ? error.code
        : undefined;

    if (errorCode === "MISSING_API_KEY" || errorCode === "ERR_MODULE_NOT_FOUND") {
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
