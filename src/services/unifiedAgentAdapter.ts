import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

interface NormalizedAgentDefinition extends AgentDefinition {
  runtime: "python" | "node" | "hybrid";
  allowedScopes: string[];
}

type ExecuteAgentMetadata = Record<string, unknown>;

interface TrustedExecutionContext {
  isAdmin?: boolean;
}

type ReasoningHook = (params: {
  agent: NormalizedAgentDefinition;
  payload: ExecuteAgentPayload;
  plan: string;
}) => Promise<string | null | undefined> | string | null | undefined;

export interface ExecuteAgentPayload {
  tenant_id: string;
  input: string;
  metadata?: ExecuteAgentMetadata;
  context?: Record<string, unknown>;
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
  code: "CONFIG_NOT_FOUND" | "SYNTAX_FAILURE" | "REGISTRY_LOAD_FAILURE";
  registryPath: string;

  constructor(
    code: "CONFIG_NOT_FOUND" | "SYNTAX_FAILURE" | "REGISTRY_LOAD_FAILURE",
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

const ALLOWED_PAYLOAD_FIELDS = ["tenant_id", "input", "metadata", "context"] as const;
const MAX_TENANT_ID_LENGTH = 128;
const MAX_INPUT_LENGTH = 8000;
const DEFAULT_PYTHON_ENGINE_TIMEOUT_MS = 15000;
const MAX_BACKEND_ERROR_SNIPPET_LENGTH = 512;
// Total outbound attempts to the Python backend (initial request + retries).
const DEFAULT_PYTHON_ENGINE_MAX_ATTEMPTS = 2;
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

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));

// ── P0: Backend URL allowlist ──────────────────────────────────────────────
function getAllowedBackendHosts(): readonly string[] {
  return (process.env.PYTHON_BACKEND_ALLOWED_HOSTS ?? "")
    .split(",")
    .map((h: string) => h.trim().toLowerCase())
    .filter(Boolean);
}

function isStrictBackendAllowlistEnforced(): boolean {
  return process.env.NODE_ENV === "production" || process.env.ENFORCE_BACKEND_ALLOWLIST === "true";
}

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
  const allowedBackendHosts = getAllowedBackendHosts();
  const strictAllowlistMode = isStrictBackendAllowlistEnforced();

  if (strictAllowlistMode && allowedBackendHosts.length === 0) {
    return { valid: false, reason: "PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled" };
  }

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return { valid: false, reason: "PYTHON_BACKEND_URL is not a valid URL" };
  }

  if (strictAllowlistMode) {
    if (parsed.protocol !== "https:") {
      return { valid: false, reason: "PYTHON_BACKEND_URL must use HTTPS" };
    }
    if (!allowedBackendHosts.includes(parsed.hostname.toLowerCase())) {
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
  if (!Number.isFinite(parsed) || parsed < 1) return DEFAULT_PYTHON_ENGINE_MAX_ATTEMPTS;
  return Math.floor(parsed);
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const RETRYABLE_TRANSPORT_CODES = new Set([
  "ECONNRESET",
  "ETIMEDOUT",
  "EAI_AGAIN",
  "ECONNREFUSED",
  "ENOTFOUND",
  "EHOSTUNREACH",
  "ENETUNREACH",
  "UND_ERR_CONNECT_TIMEOUT",
  "UND_ERR_SOCKET",
  "UND_ERR_HEADERS_TIMEOUT",
  "UND_ERR_BODY_TIMEOUT",
  "UND_ERR_REQUEST_ABORTED"
]);

function getTransportErrorCodes(error: unknown): { errorCode?: string; causeCode?: string } {
  if (!(error instanceof Error)) return {};
  const errorCode =
    "code" in error && typeof (error as NodeJS.ErrnoException).code === "string"
      ? (error as NodeJS.ErrnoException).code
      : undefined;
  const cause = "cause" in error ? (error as Error & { cause?: unknown }).cause : undefined;
  const causeCode =
    cause &&
    typeof cause === "object" &&
    "code" in cause &&
    typeof (cause as NodeJS.ErrnoException).code === "string"
      ? (cause as NodeJS.ErrnoException).code
      : undefined;
  return { errorCode, causeCode };
}

function isRetryableNetworkError(error: unknown) {
  if (!(error instanceof Error) || error.name === "AbortError") return false;
  const { errorCode, causeCode } = getTransportErrorCodes(error);
  if (errorCode && RETRYABLE_TRANSPORT_CODES.has(errorCode)) return true;
  if (causeCode && RETRYABLE_TRANSPORT_CODES.has(causeCode)) return true;
  const directCode = (error as NodeJS.ErrnoException).code;
  if (typeof directCode === "string" && RETRYABLE_TRANSPORT_CODES.has(directCode)) return true;
  return error.name === "TypeError" && error.message === "fetch failed" && Boolean(causeCode);
}

type RuntimeFailureClass = "RUNTIME_FAILURE" | "UNVERIFIED_RUNTIME" | "PYTHON_ENGINE_TIMEOUT" | "AUTH_INVALID" | "AUTH_EXPIRED";
type BlockerStatus = "AUTH_MISSING" | "AUTH_INVALID" | "AUTH_EXPIRED" | "CONFIG_NOT_FOUND" | "REGISTRY_LOAD_FAILURE" | "SYNTAX_FAILURE" | "TYPE_FAILURE" | "TEST_FAILURE" | "PYTHON_ENGINE_TIMEOUT" | "RUNTIME_FAILURE" | "WORKFLOW_CONFLICT" | "HOT_SURFACE_CONFLICT" | "SECRET_MISSING" | "DEPLOYMENT_BLOCKED" | "UNVERIFIED_RUNTIME";

class PythonEngineRuntimeError extends Error {
  code: RuntimeFailureClass;
  upstreamStatus: number | null;
  retryable: boolean;

  constructor(
    message: string,
    code: RuntimeFailureClass,
    upstreamStatus: number | null,
    retryable: boolean,
    cause?: unknown
  ) {
    super(message);
    this.name = "PythonEngineRuntimeError";
    this.code = code;
    this.upstreamStatus = upstreamStatus;
    this.retryable = retryable;
    if (cause !== undefined) {
      this.cause = cause;
    }
  }
}

class RuntimeOutputVerificationError extends Error {
  code: RuntimeFailureClass;
  reason: string;
  constructor(reason: string) {
    super(`UNVERIFIED_RUNTIME: downstream payload failed verification (${reason})`);
    this.name = "RuntimeOutputVerificationError";
    this.code = "UNVERIFIED_RUNTIME";
    this.reason = reason;
  }
}

function createPythonRuntimeError(params: { code: RuntimeFailureClass; status: number | null; retryable: boolean; correlationId?: string; message?: string; cause?: unknown; }) {
  const message = params.message ?? (params.status !== null ? buildClientSafePythonEngineError(params.status, params.correlationId) : "Python engine request failed. Please try again later.");
  return new PythonEngineRuntimeError(message, params.code, params.status, params.retryable, params.cause);
}

function truncateForDiagnostics(value: string, maxLen = 512) {
  if (value.length <= maxLen) return value;
  return `${value.slice(0, maxLen)}...(truncated)`;
}

function classifyBlocker(error: unknown): BlockerStatus {
  if (error instanceof PythonEngineRuntimeError) return error.code;
  if (error instanceof RuntimeOutputVerificationError) return error.code;
  if (error instanceof Error) {
    if (error.message.includes("CONFIG_NOT_FOUND")) return "CONFIG_NOT_FOUND";
    if (error.message.includes("REGISTRY_LOAD_FAILURE")) return "REGISTRY_LOAD_FAILURE";
    if (error.message.includes("UNAUTHORIZED_SCOPE")) return "AUTH_MISSING";
    if (error.message.includes("AUTH_INVALID")) return "AUTH_INVALID";
    if (error.message.includes("AUTH_EXPIRED")) return "AUTH_EXPIRED";
    if (error.message.includes("SECRET_MISSING")) return "SECRET_MISSING";
    return "RUNTIME_FAILURE";
  }
  return "UNVERIFIED_RUNTIME";
}

type NormalizedError = {
  message: string;
  code?: string;
  stack?: string;
};

function normalizeError(err: unknown): NormalizedError {
  const stackAllowed = process.env.NODE_ENV !== "production";
  if (err instanceof PythonEngineRuntimeError) {
    return {
      message: String(sanitizeForAudit(err.message)),
      code: err.code,
      ...(stackAllowed && err.stack ? { stack: String(sanitizeForAudit(err.stack)) } : {})
    };
  }

  if (err instanceof Error) {
    const maybeCode = "code" in err && typeof (err as { code?: unknown }).code === "string"
      ? (err as { code: string }).code
      : undefined;
    return {
      message: String(sanitizeForAudit(err.message)),
      ...(maybeCode ? { code: maybeCode } : {}),
      ...(stackAllowed && err.stack ? { stack: String(sanitizeForAudit(err.stack)) } : {})
    };
  }

  return { message: String(sanitizeForAudit(String(err))) };
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

const RUNTIME_OUTPUT_FIELDS = ["output", "message", "result", "data"] as const;

function hasValidRuntimeOutputShape(payload: Record<string, unknown>): boolean {
  return RUNTIME_OUTPUT_FIELDS.some((field) => {
    const value = payload[field];
    if (typeof value === "string") return value.trim().length > 0;
    if (value && typeof value === "object") return true;
    return false;
  });
}

export class UnifiedAgentAdapter {
  private registryPath: string;
  private agents: Map<string, NormalizedAgentDefinition> = new Map();
  private registryStartupError: RegistryStartupError | null = null;
  private policyService: PolicyService;
  private reasoningHook: ReasoningHook | null = null;

  constructor(policyService: PolicyService = new DefaultPolicyService()) {
    const moduleDefaultRegistryPath = path.resolve(MODULE_DIR, "../../.agents/config/agents.yaml");
    const moduleLegacyRegistryPath = path.resolve(MODULE_DIR, "../../agents/registry.yaml");
    const envRegistryPath = process.env.AGENT_REGISTRY_PATH?.trim();
    const resolvedEnvRegistryPath = envRegistryPath ? path.resolve(envRegistryPath) : null;

    let registryPathSource: "env" | "default" | "legacy_fallback";
    let selectedRegistryPath: string;

    if (resolvedEnvRegistryPath) {
      registryPathSource = "env";
      selectedRegistryPath = resolvedEnvRegistryPath;
    } else if (fs.existsSync(moduleDefaultRegistryPath)) {
      registryPathSource = "default";
      selectedRegistryPath = moduleDefaultRegistryPath;
    } else if (fs.existsSync(moduleLegacyRegistryPath)) {
      registryPathSource = "legacy_fallback";
      selectedRegistryPath = moduleLegacyRegistryPath;
    } else {
      registryPathSource = "default";
      selectedRegistryPath = moduleDefaultRegistryPath;
    }

    this.registryPath = selectedRegistryPath;
    this.policyService = policyService;
    logger.info(
      { registryPathSource, registryPath: selectedRegistryPath },
      "Registry startup integrity check"
    );
    this.loadRegistry();
  }

  private loadRegistry() {
    const selectedRegistryPath = this.registryPath;
    try {
      if (!fs.existsSync(selectedRegistryPath)) {
        throw new RegistryStartupError(
          "CONFIG_NOT_FOUND",
          selectedRegistryPath,
          `CONFIG_NOT_FOUND: Required registry file was not found at ${selectedRegistryPath}`
        );
      }
      const fileContents = fs.readFileSync(selectedRegistryPath, "utf8");
      let data: unknown;
      try {
        data = yaml.load(fileContents);
      } catch (parseError) {
        throw new RegistryStartupError(
          "SYNTAX_FAILURE",
          selectedRegistryPath,
          `SYNTAX_FAILURE: Failed to parse registry file at ${selectedRegistryPath}`,
          parseError
        );
      }
      let loadedAgents = 0;
      let reasoningEnabledAgents = 0;
      if (!isRecord(data)) {
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

      const rawAgents = data.agents;
      let agentsList: AgentDefinition[];
      if (Array.isArray(rawAgents)) {
        agentsList = [];
        for (let idx = 0; idx < rawAgents.length; idx++) {
          const entry = rawAgents[idx];
          if (!isRecord(entry)) {
            throw new RegistryStartupError(
              "REGISTRY_LOAD_FAILURE",
              selectedRegistryPath,
              `REGISTRY_LOAD_FAILURE: Invalid agent entry at index ${idx} (expected object)`
            );
          }
          if (typeof entry.id !== "string" || entry.id.trim().length === 0) {
            throw new RegistryStartupError(
              "REGISTRY_LOAD_FAILURE",
              selectedRegistryPath,
              `REGISTRY_LOAD_FAILURE: Invalid agent entry at index ${idx} (id must be non-empty string)`
            );
          }
          if (typeof entry.name !== "string" || entry.name.trim().length === 0) {
            throw new RegistryStartupError(
              "REGISTRY_LOAD_FAILURE",
              selectedRegistryPath,
              `REGISTRY_LOAD_FAILURE: Invalid agent ${entry.id} (name must be non-empty string)`
            );
          }
          if (entry.type !== "python" && entry.type !== "node" && entry.type !== "hybrid") {
            throw new RegistryStartupError(
              "REGISTRY_LOAD_FAILURE",
              selectedRegistryPath,
              `REGISTRY_LOAD_FAILURE: Invalid agent ${entry.id} (type must be one of python|node|hybrid)`
            );
          }
          if (typeof entry.required_scope !== "string" || entry.required_scope.trim().length === 0) {
            throw new RegistryStartupError(
              "REGISTRY_LOAD_FAILURE",
              selectedRegistryPath,
              `REGISTRY_LOAD_FAILURE: Invalid agent ${entry.id} (required_scope must be non-empty string)`
            );
          }
          agentsList.push(entry as unknown as AgentDefinition);
        }
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
      const startupError = e instanceof RegistryStartupError
        ? e
        : new RegistryStartupError(
          "REGISTRY_LOAD_FAILURE",
          selectedRegistryPath,
          `REGISTRY_LOAD_FAILURE: Failed to load registry from ${selectedRegistryPath}`,
          e
        );
      const failurePhase = startupError.code === "SYNTAX_FAILURE" ? "parse" : "schema_or_io";
      logger.error(
        { err: startupError, registryPath: selectedRegistryPath, failurePhase, failureCode: startupError.code },
        "❌ Registry Integrity Breach"
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


  setReasoningHook(reasoningHook: ReasoningHook | null) {
    this.reasoningHook = reasoningHook;
  }

  private async prepareReasoningPlan(agent: NormalizedAgentDefinition, executionPayload: ExecuteAgentPayload) {
    const generatedPlan = await this.generateExecutionPlan(agent, executionPayload);
    if (!this.reasoningHook) return generatedPlan;

    const hookResult = await this.reasoningHook({
      agent,
      payload: executionPayload,
      plan: generatedPlan
    });

    if (typeof hookResult === "string" && hookResult.trim().length > 0) {
      return hookResult;
    }

    return generatedPlan;
  }

  // P0: serverPrincipalTenantId must come from server-side auth context (session/JWT),
  // never from the request payload. The caller is responsible for deriving this value
  // from a trusted source before invoking executeAgent.
  async executeAgent(
    agentId: string,
    userId: string,
    payload: unknown,
    scopes: string[],
    serverPrincipalTenantId: string,
    trustedExecutionContext?: TrustedExecutionContext
  ) {
    if (this.registryStartupError) {
      const startupBlocker = this.registryStartupError.code;
      throw new Error(`${startupBlocker}: ${this.registryStartupError.message}`);
    }

    const agent = this.agents.get(agentId);
    if (!agent) throw new Error("Agent not found");

    const normalizedInboundPayload = this.normalizeInboundPayload(payload);
    const validation = this.validateAndSanitizePayload(normalizedInboundPayload);
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
    const correlationId = randomUUID();
    const safePayload = validation.safePayload;
    // Defensive copy — executionPayload is independent of the caller's payload.
    const currentContext =
      safePayload.context && typeof safePayload.context === "object" && !Array.isArray(safePayload.context)
        ? safePayload.context
        : {};

    const executionPayload: ExecuteAgentPayload = {
      ...safePayload,
      context: { ...currentContext },
      ...(safePayload.metadata
        ? {
            metadata: {
              ...safePayload.metadata
            }
          }
        : {})
    };
    const traceMetadata = {
      correlation_id: correlationId,
      task_id: taskId,
      agent: {
        id: agent.id,
        name: agent.name,
        runtime: agent.runtime,
        capabilities: agent.capabilities,
        reasoning_enabled: !!agent.enable_reasoning
      }
    };
    try {
      await AuditService.createTask({
        taskId,
        tenant_id: executionPayload.tenant_id,
        actor_id: userId,
        agent_id: agentId,
        metadata: {
          ...traceMetadata,
          request_metadata: sanitizeForAudit(executionPayload.metadata ?? {})
        }
      });
    } catch (error: unknown) {
      logger.error({ err: error, taskId, agentId }, "RUNTIME_FAILURE: audit task initialization failed");
      throw new Error(`RUNTIME_FAILURE: audit initialization failed for task ${taskId}`);
    }

    try {
      // PENDING -> RUNNING: AuditService.TASK_STATUS_TRANSITIONS only permits
      // PENDING -> {RUNNING, FAILED}, so a terminal COMPLETED is invalid unless
      // the task first transitions through RUNNING. Emit it before execution.
      await AuditService.updateTaskStatus(taskId, "RUNNING", traceMetadata);

      if (agent.enable_reasoning) {
        logger.info(`🧠 Agent [${agent.name}] is reasoning about the legal task...`);
        const plan = await this.prepareReasoningPlan(agent, executionPayload);
        const currentContext =
          executionPayload.context && typeof executionPayload.context === "object" && !Array.isArray(executionPayload.context)
            ? executionPayload.context
            : {};

        executionPayload.context = {
          ...currentContext,
          execution_plan: plan
        };
      }

      // P0: Audit entries sanitized before write; input body never logged.
      const action = `EXECUTE_${agent.runtime.toUpperCase()}_${agent.enable_reasoning ? "WITH" : "WITHOUT"}_REASONING`;

      await AuditService.logAction({
        tenant_id: executionPayload.tenant_id,
        actor_id: userId,
        agent_id: agentId,
        action,
        payload: { taskId, correlation_id: correlationId, reasoning_enabled: !!agent.enable_reasoning },
        metadata: traceMetadata,
        redaction_version: AUDIT_REDACTION_VERSION,
      });

      const result =
        agent.runtime === "python"
          ? await this.forwardToPythonEngine(agent, executionPayload, userId, taskId)
          : await this.executeNodeInternal(agent, executionPayload, trustedExecutionContext?.isAdmin ?? false);

      const verifiedResult = await this.verifyOutputQuality(result);

      // P0: Sanitize result before audit write — never log raw LLM output or legal text.
      await AuditService.updateTaskStatus(taskId, "COMPLETED", {
        ...traceMetadata,
        result: sanitizeForAudit(verifiedResult)
      });

      return { taskId, status: "success", data: verifiedResult };
    } catch (error: unknown) {
      const safeErrorMessage = error instanceof Error ? error.message : String(error);
      const originalStack = error instanceof Error && error.stack ? error.stack : undefined;
      const blocker = classifyBlocker(error);
      const normalizedError = normalizeError(error);
      const structuredFailure = error instanceof PythonEngineRuntimeError
        ? { failure_class: error.code, upstream_status: error.upstreamStatus, retryable: error.retryable }
        : { failure_class: blocker, upstream_status: null };

      logger.error(
        { err: error, agentId, structuredFailure, normalizedError, ...(originalStack ? { originalStack } : {}) },
        `💥 Intelligence Failure at Agent ${agentId}`
      );
      await AuditService.updateTaskStatus(taskId, "FAILED", {
        error: String(sanitizeForAudit(safeErrorMessage)),
        ...(normalizedError.code ? { code: normalizedError.code } : {}),
        ...(normalizedError.stack ? { stack: normalizedError.stack } : {}),
        blocker,
        ...structuredFailure
      });
      throw error;
    }
  }

  private normalizeInboundPayload(payload: unknown): Record<string, unknown> {
    const rawPayload = payload && typeof payload === "object" && !Array.isArray(payload)
      ? (payload as Record<string, unknown>)
      : {};

    const normalizedContext =
      rawPayload.context && typeof rawPayload.context === "object" && !Array.isArray(rawPayload.context)
        ? (rawPayload.context as Record<string, unknown>)
        : {};

    return {
      ...rawPayload,
      context: normalizedContext
    };
  }

  private validateAndSanitizePayload(payload: unknown): ValidationResult {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return { isValid: false, reason: "tenant_id is required and must be a non-empty string" };
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

    let safeContext: Record<string, unknown> | undefined;
    if (rawPayload.context !== undefined) {
      if (!rawPayload.context || typeof rawPayload.context !== "object" || Array.isArray(rawPayload.context)) {
        return { isValid: false, reason: "context must be an object when provided" };
      }
      safeContext = rawPayload.context as Record<string, unknown>;
    }

    return {
      isValid: true,
      safePayload: {
        tenant_id: rawPayload.tenant_id.trim(),
        input: rawPayload.input,
        ...(safeMetadata ? { metadata: safeMetadata } : {}),
        ...(safeContext ? { context: safeContext } : {})
      }
    };
  }

  private async generateExecutionPlan(_agent: NormalizedAgentDefinition, _payload: ExecuteAgentPayload) {
    return "1. تحليل السؤال القانوني. 2. استرجاع السوابق عبر RAPTOR. 3. مطابقة المخرجات مع نظام PDPL.";
  }

  private async verifyOutputQuality(result: unknown) {
    if (!result || typeof result !== "object" || Array.isArray(result)) {
      throw new RuntimeOutputVerificationError("payload must be a non-empty object");
    }

    const output = result as Record<string, unknown>;
    if (Object.keys(output).length === 0) {
      throw new RuntimeOutputVerificationError("payload object is empty");
    }

    if (!hasValidRuntimeOutputShape(output)) {
      throw new RuntimeOutputVerificationError("required runtime output field is missing or malformed");
    }

    return result;
  }

  private validatePythonEngineResponseSchema(result: unknown) {
    if (!result || typeof result !== "object" || Array.isArray(result)) {
      throw createPythonRuntimeError({
        code: "RUNTIME_FAILURE",
        status: 502,
        retryable: false,
        message: "RUNTIME_FAILURE: python engine response must be a JSON object"
      });
    }

    const payload = result as Record<string, unknown>;
    if (!hasValidRuntimeOutputShape(payload)) {
      throw createPythonRuntimeError({
        code: "RUNTIME_FAILURE",
        status: 502,
        retryable: false,
        message: "RUNTIME_FAILURE: python engine response schema validation failed"
      });
    }

    return payload;
  }


  private async readErrorBodySafely(response: Response) {
    try {
      const rawText = await response.text();
      if (!rawText.trim()) return "<empty>";
      try {
        return truncateForDiagnostics(JSON.stringify(JSON.parse(rawText)));
      } catch {
        return truncateForDiagnostics(rawText);
      }
    } catch {
      return "<unavailable>";
    }
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
    const safeBody = { agent_id: agent.id, tenant_id: validation.safePayload.tenant_id, input: validation.safePayload.input, metadata: validation.safePayload.metadata ?? {}, context: validation.safePayload.context ?? {} };
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
    // Contract: PYTHON_BACKEND_MAX_ATTEMPTS is the total number of outbound attempts.
    const maxAttempts = getPythonEngineMaxAttempts();
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const abortController = new AbortController();
      const timeoutHandle = setTimeout(() => abortController.abort(), timeoutMs);
      const requestId = randomUUID();

      try {
        const response = await fetch(`${normalizedBackendUrl}/api/v1/workflow/query`, { method: "POST", headers: { "Content-Type": "application/json", "x-request-id": requestId, "x-task-id": taskId }, body: JSON.stringify(safeBody), signal: abortController.signal });
        if (!response.ok) {
          const rawError = await this.readErrorBodySafely(response);
          const retryable = RETRYABLE_HTTP_STATUSES.has(response.status);
          const mappedCode: RuntimeFailureClass = response.status === 401 ? "AUTH_INVALID" : response.status === 403 ? "AUTH_EXPIRED" : "RUNTIME_FAILURE";
          if (retryable && attempt < maxAttempts) { await sleep(DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS * 2 ** (attempt - 1)); continue; }
          const correlationId = randomUUID().slice(0, 8);
          await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_DOWNSTREAM_FAILURE", {
            status_code: response.status,
            status_text: response.statusText || "missing",
            correlation_id: correlationId,
            request_id: requestId,
            task_id: taskId,
            endpoint,
            backend_error_fingerprint: String(
              sanitizeForAudit(sanitizeBackendErrorForAudit(rawError))
            ).length
          });
          throw createPythonRuntimeError({ code: mappedCode, status: response.status, retryable, correlationId, message: `${mappedCode}: Python engine returned HTTP ${response.status} ${response.statusText || "unknown"}` });
        }

        const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
        if (!contentType.includes("application/json")) {
          const correlationId = randomUUID().slice(0, 8);
          const rawPayload = await response.text();
          await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_CONTENT_TYPE_MISMATCH", { status_code: response.status, content_type: contentType || "missing", correlation_id: correlationId, request_id: requestId, task_id: taskId, endpoint, backend_error_excerpt: sanitizeForAudit(sanitizeBackendErrorForAudit(rawPayload)) });
          throw createPythonRuntimeError({ code: "UNVERIFIED_RUNTIME", status: response.status, retryable: false, correlationId });
        }

        try {
          const parsed = await response.json();
          return this.validatePythonEngineResponseSchema(parsed);
        }
        catch (parseError) {
          const correlationId = randomUUID().slice(0, 8);
          await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_JSON_PARSE_FAILURE", { status_code: response.status, correlation_id: correlationId, request_id: requestId, task_id: taskId, endpoint });
          throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: response.status, retryable: false, correlationId, message: `RUNTIME_FAILURE: malformed JSON payload from python engine (HTTP ${response.status})`, cause: parseError });
        }
      } catch (error) {
        if ((error instanceof Error && error.name === "AbortError") || abortController.signal.aborted) throw createPythonRuntimeError({ code: "PYTHON_ENGINE_TIMEOUT", status: null, retryable: false, message: `Python engine timed out after ${timeoutMs}ms for agent ${agent.id}`, cause: error });
        if (error instanceof PythonEngineRuntimeError) throw error;
        const { errorCode, causeCode } = getTransportErrorCodes(error);
        const retryable = isRetryableNetworkError(error);
        logger.error({
          classification: "RUNTIME_FAILURE",
          stage: "python_engine_fetch",
          attempt,
          maxAttempts,
          timeoutMs,
          retryable,
          errorName: error instanceof Error ? error.name : "UnknownError",
          errorCode: errorCode ?? null,
          causeName: error instanceof Error && "cause" in error && (error as Error & { cause?: unknown }).cause instanceof Error
            ? ((error as Error & { cause?: Error }).cause?.name ?? null)
            : null,
          causeCode: causeCode ?? null
        }, "Python engine fetch failed");
        if (retryable && attempt < maxAttempts) { await sleep(DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS * 2 ** (attempt - 1)); continue; }
        const correlationId = randomUUID().slice(0, 8);
        await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_REQUEST_FAILURE", { correlation_id: correlationId, request_id: requestId, endpoint, task_id: taskId, error_code: (error as NodeJS.ErrnoException).code ?? "UNKNOWN", error_name: error instanceof Error ? error.name : "UNKNOWN" });
        throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: 502, retryable: false, correlationId, message: "RUNTIME_FAILURE: python engine request transport failure", cause: error });
      } finally { clearTimeout(timeoutHandle); }
    }
    throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: null, retryable: false, message: "RUNTIME_FAILURE: python engine exhausted retry budget" });
  }

  /**
   * Node/hybrid split behavior (intentional):
   * - python runtime -> Python backend forwarding path
   * - node runtime   -> canonical Node runner (runAgent)
   * - hybrid runtime -> canonical Node runner (runAgent) with validated payload passthrough
   */
  private async executeNodeInternal(
    agent: NormalizedAgentDefinition,
    payload: ExecuteAgentPayload,
    isAdmin: boolean
  ) {
    const dispatchPayload = {
      tenant_id: payload.tenant_id,
      input: payload.input,
      metadata: payload.metadata ?? {},
      context: payload.context ?? {}
    };

    try {
      const runAgent = await this.getNodeDispatcher();

      return await runAgent({
        agentId: agent.id,
        input: payload.input,
        payload: dispatchPayload,
        context: "api",
        isAdmin
      });
    } catch (error: unknown) {
      throw this.mapNodeExecutionError(agent.id, error);
    }
  }

  private async getNodeDispatcher() {
    const nodeRuntimeModule = await import("../runners/agentRunner.js");
    return nodeRuntimeModule.runAgent;
  }

  private isNodeRunnerModuleNotFound(error: unknown) {
    if (!(error instanceof Error)) {
      return false;
    }

    const err = error as NodeJS.ErrnoException & { url?: string };
    const code = err.code;
    const isModuleNotFound =
      code === "ERR_MODULE_NOT_FOUND" || code === "MODULE_NOT_FOUND";
    if (!isModuleNotFound) {
      return false;
    }

    const runnerSpecifier = "agentrunner.js";

    if (typeof err.url === "string") {
      return err.url.toLowerCase().endsWith(runnerSpecifier);
    }

    const match = /cannot find (?:module|package) ['"]([^'"]+)['"]/i.exec(
      err.message
    );
    if (match) {
      return match[1].toLowerCase().endsWith(runnerSpecifier);
    }

    return false;
  }

  private mapNodeExecutionError(agentId: string, error: unknown) {
    if (error instanceof NodeExecutionDispatchError) {
      return error;
    }

    if (!(error instanceof Error)) {
      return error;
    }

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

    if (this.isNodeRunnerModuleNotFound(error)) {
      return new NodeExecutionDispatchError(
        agentId,
        "CONFIG_NOT_FOUND",
        `CONFIG_NOT_FOUND: Node dispatcher module missing for agent ${agentId}`,
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
