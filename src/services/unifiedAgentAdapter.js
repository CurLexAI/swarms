import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import yaml from "js-yaml";
import { randomUUID } from "crypto";
import logger from "../utils/logger.js";
import { AuditService } from "./AuditService.js";
import { buildClientSafePythonEngineError, sanitizeBackendErrorForAudit } from "./unifiedAgentAdapterErrorUtils.js";
export class RegistryStartupError extends Error {
    code;
    registryPath;
    constructor(code, registryPath, message, cause) {
        super(message);
        this.name = "RegistryStartupError";
        this.code = code;
        this.registryPath = registryPath;
        if (cause !== undefined) {
            this.cause = cause;
        }
    }
}
const ALLOWED_PAYLOAD_FIELDS = ["tenant_id", "input", "metadata", "context"];
const MAX_TENANT_ID_LENGTH = 128;
const MAX_INPUT_LENGTH = 8000;
const DEFAULT_PYTHON_ENGINE_TIMEOUT_MS = 15000;
const MAX_BACKEND_ERROR_SNIPPET_LENGTH = 512;
// Total outbound attempts to the Python backend (initial request + retries).
const DEFAULT_PYTHON_ENGINE_MAX_ATTEMPTS = 2;
const DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS = 250;
const RETRYABLE_HTTP_STATUSES = new Set([502, 503, 504]);
const CLIENT_SAFE_PYTHON_ENGINE_ERROR_PATTERN = /^Python engine request failed with status \d+\. Please try again later(?: \(ref: [0-9a-f]{8}\))?\.$/i;
// ── P0: Capability enforcement ─────────────────────────────────────────────
// Maps agent runtime to the required declared capability.
// Agents must declare matching capabilities in .agents/config/agents.yaml to be executed.
const RUNTIME_CAPABILITY_MAP = {
    python: "python_execution",
    node: "node_execution",
    hybrid: "node_execution",
};
const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
// ── P0: Backend URL allowlist ──────────────────────────────────────────────
function getAllowedBackendHosts() {
    return (process.env.PYTHON_BACKEND_ALLOWED_HOSTS ?? "")
        .split(",")
        .map((h) => h.trim().toLowerCase())
        .filter(Boolean);
}
function isStrictBackendAllowlistEnforced() {
    return process.env.NODE_ENV === "production" || process.env.ENFORCE_BACKEND_ALLOWLIST === "true";
}
// ── P0: Audit redaction ────────────────────────────────────────────────────
const AUDIT_REDACTION_VERSION = "1";
const MAX_AUDIT_STRING_LENGTH = 500;
const SENSITIVE_PATTERNS = [
    /Bearer\s+[\w._~+/-]+=*/gi,
    /sk-[\w]{20,}/g,
    /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
    /\b\d{10}\b/g, // national IDs (10-digit)
];
function sanitizeForAudit(value) {
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
        return Object.fromEntries(Object.entries(value).map(([k, v]) => [
            k,
            sanitizeForAudit(v),
        ]));
    }
    return value;
}
function validateBackendUrl(url) {
    const allowedBackendHosts = getAllowedBackendHosts();
    const strictAllowlistMode = isStrictBackendAllowlistEnforced();
    if (strictAllowlistMode && allowedBackendHosts.length === 0) {
        return { valid: false, reason: "PYTHON_BACKEND_ALLOWED_HOSTS is required when strict backend allowlist mode is enabled" };
    }
    let parsed;
    try {
        parsed = new URL(url);
    }
    catch {
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
class DefaultPolicyService {
    authorizeAgentExecution(request) {
        const { tenantId, principalTenantId, agent, actorScopes, requestedCapabilities, scopeHierarchy } = request;
        if (tenantId !== principalTenantId)
            return { allowed: false, matchedRule: "tenant_boundary", reasonCode: "CROSS_TENANT_ACCESS_DENIED" };
        const effectiveScopes = new Set(actorScopes);
        for (const scope of actorScopes) {
            for (const inheritedScope of scopeHierarchy?.[scope] ?? [])
                effectiveScopes.add(inheritedScope);
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
    if (!Number.isFinite(parsed) || parsed < 1)
        return DEFAULT_PYTHON_ENGINE_MAX_ATTEMPTS;
    return Math.floor(parsed);
}
function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
function isRetryableNetworkError(error) {
    if (!(error instanceof Error) || error.name === "AbortError")
        return false;
    const code = error.code;
    return code === "ECONNRESET" || code === "ETIMEDOUT" || code === "EAI_AGAIN" || code === "UND_ERR_CONNECT_TIMEOUT";
}
class PythonEngineRuntimeError extends Error {
    code;
    upstreamStatus;
    retryable;
    constructor(message, code, upstreamStatus, retryable, cause) {
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
    code;
    reason;
    constructor(reason) {
        super(`UNVERIFIED_RUNTIME: downstream payload failed verification (${reason})`);
        this.name = "RuntimeOutputVerificationError";
        this.code = "UNVERIFIED_RUNTIME";
        this.reason = reason;
    }
}
function createPythonRuntimeError(params) {
    const message = params.message ?? (params.status !== null ? buildClientSafePythonEngineError(params.status, params.correlationId) : "Python engine request failed. Please try again later.");
    return new PythonEngineRuntimeError(message, params.code, params.status, params.retryable, params.cause);
}
function truncateForDiagnostics(value, maxLen = 512) {
    if (value.length <= maxLen)
        return value;
    return `${value.slice(0, maxLen)}...(truncated)`;
}
function classifyBlocker(error) {
    if (error instanceof PythonEngineRuntimeError)
        return error.code;
    if (error instanceof RuntimeOutputVerificationError)
        return error.code;
    if (error instanceof Error) {
        if (error.message.includes("CONFIG_NOT_FOUND"))
            return "CONFIG_NOT_FOUND";
        if (error.message.includes("REGISTRY_LOAD_FAILURE"))
            return "REGISTRY_LOAD_FAILURE";
        if (error.message.includes("UNAUTHORIZED_SCOPE"))
            return "AUTH_MISSING";
        if (error.message.includes("AUTH_INVALID"))
            return "AUTH_INVALID";
        if (error.message.includes("AUTH_EXPIRED"))
            return "AUTH_EXPIRED";
        if (error.message.includes("SECRET_MISSING"))
            return "SECRET_MISSING";
        return "RUNTIME_FAILURE";
    }
    return "UNVERIFIED_RUNTIME";
}
function normalizeError(err) {
    const stackAllowed = process.env.NODE_ENV !== "production";
    if (err instanceof PythonEngineRuntimeError) {
        return {
            message: String(sanitizeForAudit(err.message)),
            code: err.code,
            ...(stackAllowed && err.stack ? { stack: String(sanitizeForAudit(err.stack)) } : {})
        };
    }
    if (err instanceof Error) {
        const maybeCode = "code" in err && typeof err.code === "string"
            ? err.code
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
    code;
    classification;
    agentId;
    constructor(agentId, code, message, cause) {
        super(message);
        this.name = "NodeExecutionDispatchError";
        this.agentId = agentId;
        this.code = code;
        this.classification = code === "CONFIG_NOT_FOUND" ? "CONFIG_FAILURE" : "RUNTIME_FAILURE";
        if (cause !== undefined)
            this.cause = cause;
    }
}
export class UnifiedAgentAdapter {
    registryPath;
    agents = new Map();
    registryStartupError = null;
    policyService;
    reasoningHook = null;
    constructor(policyService = new DefaultPolicyService()) {
        const moduleDefaultRegistryPath = path.resolve(MODULE_DIR, "../../.agents/config/agents.yaml");
        const moduleLegacyRegistryPath = path.resolve(MODULE_DIR, "../../agents/registry.yaml");
        const envRegistryPath = process.env.AGENT_REGISTRY_PATH?.trim();
        const resolvedEnvRegistryPath = envRegistryPath ? path.resolve(envRegistryPath) : null;
        let registryPathSource;
        let selectedRegistryPath;
        if (resolvedEnvRegistryPath) {
            registryPathSource = "env";
            selectedRegistryPath = resolvedEnvRegistryPath;
        }
        else if (fs.existsSync(moduleDefaultRegistryPath)) {
            registryPathSource = "default";
            selectedRegistryPath = moduleDefaultRegistryPath;
        }
        else if (fs.existsSync(moduleLegacyRegistryPath)) {
            registryPathSource = "legacy_fallback";
            selectedRegistryPath = moduleLegacyRegistryPath;
        }
        else {
            registryPathSource = "default";
            selectedRegistryPath = moduleDefaultRegistryPath;
        }
        this.registryPath = selectedRegistryPath;
        this.policyService = policyService;
        logger.info({ registryPathSource, registryPath: selectedRegistryPath }, "Registry startup integrity check");
        this.loadRegistry();
    }
    loadRegistry() {
        const selectedRegistryPath = this.registryPath;
        try {
            if (!fs.existsSync(selectedRegistryPath)) {
                throw new RegistryStartupError("CONFIG_NOT_FOUND", selectedRegistryPath, `CONFIG_NOT_FOUND: Required registry file was not found at ${selectedRegistryPath}`);
            }
            const fileContents = fs.readFileSync(selectedRegistryPath, "utf8");
            let data;
            try {
                data = yaml.load(fileContents);
            }
            catch (parseError) {
                throw new RegistryStartupError("SYNTAX_FAILURE", selectedRegistryPath, `SYNTAX_FAILURE: Failed to parse registry file at ${selectedRegistryPath}`, parseError);
            }
            let loadedAgents = 0;
            let reasoningEnabledAgents = 0;
            if (!data || typeof data !== "object" || Array.isArray(data)) {
                throw new RegistryStartupError("REGISTRY_LOAD_FAILURE", selectedRegistryPath, `REGISTRY_LOAD_FAILURE: Invalid registry schema in ${selectedRegistryPath} (expected top-level object)`);
            }
            if (!("agents" in data)) {
                throw new RegistryStartupError("REGISTRY_LOAD_FAILURE", selectedRegistryPath, `REGISTRY_LOAD_FAILURE: Invalid registry schema in ${selectedRegistryPath} (missing agents key)`);
            }
            const rawAgents = data.agents;
            let agentsList;
            if (Array.isArray(rawAgents)) {
                agentsList = [];
                for (let idx = 0; idx < rawAgents.length; idx++) {
                    const entry = rawAgents[idx];
                    if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
                        logger.warn({ index: idx, entryType: Array.isArray(entry) ? "array" : typeof entry }, "Skipping non-object agent entry in registry");
                        continue;
                    }
                    const e = entry;
                    const candidateId = typeof e.id === "string" && e.id.trim().length > 0 ? e.id.trim() : null;
                    if (!candidateId) {
                        logger.warn({ index: idx, hasIdField: Object.prototype.hasOwnProperty.call(e, "id") }, "Skipping agent entry with missing or empty id");
                        continue;
                    }
                    agentsList.push(entry);
                }
            }
            else if (rawAgents && typeof rawAgents === "object") {
                agentsList = Object.entries(rawAgents).map(([key, raw]) => {
                    const r = raw ?? {};
                    const runtime = r.execution?.runtime ?? (r.type ?? "python");
                    return {
                        id: r.id ?? key,
                        name: r.name ?? r.display_name ?? key,
                        role: r.role ?? r.capability ?? key,
                        type: runtime,
                        execution: { runtime },
                        capabilities: r.capabilities ??
                            [RUNTIME_CAPABILITY_MAP[runtime] ?? "python_execution"],
                        contexts: r.contexts,
                        required_scope: r.required_scope,
                        enable_reasoning: r.enable_reasoning,
                        category: r.category,
                    };
                });
            }
            else {
                throw new RegistryStartupError("REGISTRY_LOAD_FAILURE", selectedRegistryPath, `REGISTRY_LOAD_FAILURE: Invalid registry schema in ${selectedRegistryPath} (agents must be array or mapping)`);
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
            logger.info({
                loadedAgents,
                reasoningEnabledAgents,
                registryPath: selectedRegistryPath
            }, "✅ LexPrim Intelligence Matrix loaded");
        }
        catch (e) {
            logger.error({ err: e }, "❌ Registry Integrity Breach");
            const startupError = e instanceof RegistryStartupError
                ? e
                : new RegistryStartupError("REGISTRY_LOAD_FAILURE", selectedRegistryPath, `REGISTRY_LOAD_FAILURE: Failed to load registry from ${selectedRegistryPath}`, e);
            this.registryStartupError = startupError;
            throw startupError;
        }
    }
    getServiceHealth() {
        if (this.registryStartupError) {
            return {
                status: "unhealthy",
                reason: this.registryStartupError.code,
                message: this.registryStartupError.message,
                registryPath: this.registryStartupError.registryPath
            };
        }
        return {
            status: "healthy",
            agentsLoaded: this.agents.size,
            registryPath: this.registryPath
        };
    }
    setReasoningHook(reasoningHook) {
        this.reasoningHook = reasoningHook;
    }
    async prepareReasoningPlan(agent, executionPayload) {
        const generatedPlan = await this.generateExecutionPlan(agent, executionPayload);
        if (!this.reasoningHook)
            return generatedPlan;
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
    async executeAgent(agentId, userId, payload, scopes, serverPrincipalTenantId, trustedExecutionContext) {
        if (this.registryStartupError) {
            const startupBlocker = this.registryStartupError.code;
            throw new Error(`${startupBlocker}: ${this.registryStartupError.message}`);
        }
        const agent = this.agents.get(agentId);
        if (!agent)
            throw new Error("Agent not found");
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
            const auditDetails = {
                matched_rule: authorizationDecision.matchedRule,
                reason_code: authorizationDecision.reasonCode,
                redaction_version: AUDIT_REDACTION_VERSION
            };
            if (authorizationDecision.reasonCode === "CAPABILITY_DENIED") {
                auditDetails.required_capabilities = requestedCapabilities;
                auditDetails.agent_capabilities = agent.capabilities;
            }
            await AuditService.logSecurityViolation(userId, agentId, authorizationDecision.reasonCode, auditDetails);
            logger.warn({
                actorId: userId,
                agentId,
                matchedRule: authorizationDecision.matchedRule,
                reasonCode: authorizationDecision.reasonCode
            }, "Agent execution denied by policy evaluator");
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
        // Defensive copy — executionPayload is independent of the caller's payload.
        const currentContext = safePayload.context && typeof safePayload.context === "object" && !Array.isArray(safePayload.context)
            ? safePayload.context
            : {};
        const executionPayload = {
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
        try {
            await AuditService.createTask({
                taskId,
                tenant_id: executionPayload.tenant_id,
                actor_id: userId,
                agent_id: agentId,
                metadata: {
                    runtime: agent.runtime,
                    reasoning_enabled: !!agent.enable_reasoning,
                    request_metadata: sanitizeForAudit(executionPayload.metadata ?? {})
                }
            });
        }
        catch (error) {
            logger.error({ err: error, taskId, agentId }, "RUNTIME_FAILURE: audit task initialization failed");
            throw new Error(`RUNTIME_FAILURE: audit initialization failed for task ${taskId}`);
        }
        if (agent.enable_reasoning) {
            logger.info(`🧠 Agent [${agent.name}] is reasoning about the legal task...`);
            const plan = await this.prepareReasoningPlan(agent, executionPayload);
            const currentContext = executionPayload.context && typeof executionPayload.context === "object" && !Array.isArray(executionPayload.context)
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
            payload: { taskId, reasoning_enabled: !!agent.enable_reasoning },
            redaction_version: AUDIT_REDACTION_VERSION,
        });
        try {
            const result = agent.runtime === "python"
                ? await this.forwardToPythonEngine(agent, executionPayload, userId, taskId)
                : await this.executeNodeInternal(agent, executionPayload, trustedExecutionContext?.isAdmin ?? false);
            const verifiedResult = await this.verifyOutputQuality(result);
            // P0: Sanitize result before audit write — never log raw LLM output or legal text.
            await AuditService.updateTaskStatus(taskId, "COMPLETED", sanitizeForAudit(verifiedResult));
            return { taskId, status: "success", data: verifiedResult };
        }
        catch (error) {
            const safeErrorMessage = error instanceof Error ? error.message : String(error);
            const originalStack = error instanceof Error && error.stack ? error.stack : undefined;
            const blocker = classifyBlocker(error);
            const normalizedError = normalizeError(error);
            const structuredFailure = error instanceof PythonEngineRuntimeError
                ? { failure_class: error.code, upstream_status: error.upstreamStatus, retryable: error.retryable }
                : { failure_class: blocker, upstream_status: null };
            logger.error({ err: error, agentId, structuredFailure, normalizedError, ...(originalStack ? { originalStack } : {}) }, `💥 Intelligence Failure at Agent ${agentId}`);
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
    validateAndSanitizePayload(payload) {
        if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
            return { isValid: false, reason: "Payload must be an object" };
        }
        const rawPayload = payload;
        const unknownFields = Object.keys(rawPayload).filter((key) => !ALLOWED_PAYLOAD_FIELDS.includes(key));
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
        let safeMetadata;
        if (rawPayload.metadata !== undefined) {
            if (!rawPayload.metadata || typeof rawPayload.metadata !== "object" || Array.isArray(rawPayload.metadata)) {
                return { isValid: false, reason: "metadata must be an object when provided" };
            }
            safeMetadata = rawPayload.metadata;
        }
        let safeContext;
        if (rawPayload.context !== undefined) {
            if (!rawPayload.context || typeof rawPayload.context !== "object" || Array.isArray(rawPayload.context)) {
                return { isValid: false, reason: "context must be an object when provided" };
            }
            safeContext = rawPayload.context;
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
    async generateExecutionPlan(_agent, _payload) {
        return "1. تحليل السؤال القانوني. 2. استرجاع السوابق عبر RAPTOR. 3. مطابقة المخرجات مع نظام PDPL.";
    }
    async verifyOutputQuality(result) {
        if (!result || typeof result !== "object" || Array.isArray(result)) {
            throw new RuntimeOutputVerificationError("payload must be a non-empty object");
        }
        const output = result;
        const keys = Object.keys(output);
        if (keys.length === 0) {
            throw new RuntimeOutputVerificationError("payload object is empty");
        }
        const hasValidOutputField = ["output", "message", "result", "data"].some((field) => {
            const value = output[field];
            if (typeof value === "string")
                return value.trim().length > 0;
            if (value && typeof value === "object")
                return true;
            return false;
        });
        if (!hasValidOutputField) {
            throw new RuntimeOutputVerificationError("required runtime output field is missing or malformed");
        }
        return result;
    }
    async forwardToPythonEngine(agent, payload, userId, taskId) {
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
        if (!urlValidation.valid)
            throw new Error(`CONFIG_NOT_FOUND: ${urlValidation.reason}`);
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
                    const rawError = truncateForDiagnostics(await response.text());
                    const retryable = RETRYABLE_HTTP_STATUSES.has(response.status);
                    const mappedCode = response.status === 401 ? "AUTH_INVALID" : response.status === 403 ? "AUTH_EXPIRED" : "RUNTIME_FAILURE";
                    if (retryable && attempt < maxAttempts) {
                        await sleep(DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS * 2 ** (attempt - 1));
                        continue;
                    }
                    const correlationId = randomUUID().slice(0, 8);
                    await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_DOWNSTREAM_FAILURE", { status_code: response.status, status_text: response.statusText || "missing", correlation_id: correlationId, request_id: requestId, endpoint, backend_error_excerpt: sanitizeForAudit(sanitizeBackendErrorForAudit(rawError)) });
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
                    return await response.json();
                }
                catch (parseError) {
                    const correlationId = randomUUID().slice(0, 8);
                    await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_JSON_PARSE_FAILURE", { status_code: response.status, correlation_id: correlationId, request_id: requestId, task_id: taskId, endpoint });
                    throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: response.status, retryable: false, correlationId, message: `RUNTIME_FAILURE: malformed JSON payload from python engine (HTTP ${response.status})`, cause: parseError });
                }
            }
            catch (error) {
                if ((error instanceof Error && error.name === "AbortError") || abortController.signal.aborted)
                    throw createPythonRuntimeError({ code: "PYTHON_ENGINE_TIMEOUT", status: null, retryable: false, message: `Python engine timed out after ${timeoutMs}ms for agent ${agent.id}`, cause: error });
                if (error instanceof PythonEngineRuntimeError)
                    throw error;
                if (isRetryableNetworkError(error) && attempt < maxAttempts) {
                    await sleep(DEFAULT_PYTHON_ENGINE_BACKOFF_BASE_MS * 2 ** (attempt - 1));
                    continue;
                }
                const correlationId = randomUUID().slice(0, 8);
                await AuditService.logSecurityViolation(userId, agent.id, "PYTHON_ENGINE_REQUEST_FAILURE", { correlation_id: correlationId, request_id: requestId, endpoint, task_id: taskId });
                throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: 502, retryable: false, correlationId, message: "RUNTIME_FAILURE: python engine request transport failure", cause: error });
            }
            finally {
                clearTimeout(timeoutHandle);
            }
        }
        throw createPythonRuntimeError({ code: "RUNTIME_FAILURE", status: null, retryable: false, message: "RUNTIME_FAILURE: python engine exhausted retry budget" });
    }
    /**
     * Node/hybrid split behavior (intentional):
     * - python runtime -> Python backend forwarding path
     * - node runtime   -> canonical Node runner (runAgent)
     * - hybrid runtime -> canonical Node runner (runAgent) with validated payload passthrough
     */
    async executeNodeInternal(agent, payload, isAdmin) {
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
        }
        catch (error) {
            throw this.mapNodeExecutionError(agent.id, error);
        }
    }
    async getNodeDispatcher() {
        const nodeRuntimeModule = await import("../runners/agentRunner.js");
        return nodeRuntimeModule.runAgent;
    }
    isNodeRunnerModuleNotFound(error) {
        if (!(error instanceof Error)) {
            return false;
        }
        const err = error;
        const code = err.code;
        const isModuleNotFound = code === "ERR_MODULE_NOT_FOUND" || code === "MODULE_NOT_FOUND";
        if (!isModuleNotFound) {
            return false;
        }
        const runnerSpecifier = "agentrunner.js";
        if (typeof err.url === "string") {
            return err.url.toLowerCase().endsWith(runnerSpecifier);
        }
        const match = /cannot find (?:module|package) ['"]([^'"]+)['"]/i.exec(err.message);
        if (match) {
            return match[1].toLowerCase().endsWith(runnerSpecifier);
        }
        return false;
    }
    mapNodeExecutionError(agentId, error) {
        if (error instanceof NodeExecutionDispatchError) {
            return error;
        }
        if (!(error instanceof Error)) {
            return error;
        }
        const errorCode = typeof error === "object" && error !== null && "code" in error && typeof error.code === "string"
            ? error.code
            : undefined;
        if (errorCode === "MISSING_API_KEY") {
            return new NodeExecutionDispatchError(agentId, "CONFIG_NOT_FOUND", `CONFIG_NOT_FOUND: Node runtime configuration missing for agent ${agentId}`, error);
        }
        if (this.isNodeRunnerModuleNotFound(error)) {
            return new NodeExecutionDispatchError(agentId, "CONFIG_NOT_FOUND", `CONFIG_NOT_FOUND: Node dispatcher module missing for agent ${agentId}`, error);
        }
        const message = error instanceof Error ? error.message : "Node agent execution failed";
        return new NodeExecutionDispatchError(agentId, "RUNTIME_FAILURE", `RUNTIME_FAILURE: Node runtime execution failed for agent ${agentId}: ${message}`, error);
    }
}
export const agentAdapter = new UnifiedAgentAdapter();
