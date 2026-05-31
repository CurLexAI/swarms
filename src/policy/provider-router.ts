import {
  evaluateRuntimePolicy,
  type DataClassification,
  type ProviderId,
  type RuntimePolicyDecision,
  RuntimePolicyError,
  type RuntimePolicyRequest,
} from "./runtime-policy.js";

export interface RouteRequest {
  readonly prompt: string;
  readonly classification: DataClassification;
  readonly tenantId: string;
  readonly traceId: string;
  readonly requiresVision?: boolean;
  readonly requiresLongContext?: boolean;
  readonly requiresCodeGeneration?: boolean;
  readonly humanApprovedCloudEgress?: boolean;
  readonly metadata?: Readonly<Record<string, unknown>>;
}

export interface LlmProviderResponse {
  readonly text: string;
  readonly usage?: Readonly<Record<string, number>>;
  readonly metadata?: Readonly<Record<string, unknown>>;
}

export interface LlmProvider {
  readonly id: ProviderId;
  isAvailable(): Promise<boolean> | boolean;
  generate(request: RouteRequest): Promise<LlmProviderResponse> | LlmProviderResponse;
}

export type AuditEventType =
  | "classification_decision"
  | "provider_rejected"
  | "provider_unavailable"
  | "provider_selected"
  | "no_allowed_provider";

export interface AuditEvent {
  readonly type: AuditEventType;
  readonly tenantId: string;
  readonly traceId: string;
  readonly providerId?: ProviderId;
  readonly payload: Readonly<Record<string, unknown>>;
  readonly occurredAt: string;
}

export interface AuditSink {
  record(event: AuditEvent): Promise<void> | void;
}

export interface AuditedClassificationDecision {
  readonly classification: DataClassification;
  readonly policy: RuntimePolicyDecision;
}

export interface ProviderRejectionEvent {
  readonly providerId: ProviderId;
  readonly reason: string;
}

export interface ProviderUnavailabilityEvent {
  readonly providerId: ProviderId;
  readonly reason: "PROVIDER_NOT_REGISTERED" | "PROVIDER_UNAVAILABLE" | "PROVIDER_ERROR";
}

export interface RouteDecision {
  readonly providerId: ProviderId;
  readonly response: LlmProviderResponse;
  readonly classificationDecision: AuditedClassificationDecision;
  readonly rejectedProviders: readonly ProviderRejectionEvent[];
  readonly unavailableProviders: readonly ProviderUnavailabilityEvent[];
}

export class ProviderRouterError extends Error {
  public readonly code: "NO_ALLOWED_PROVIDER";
  public readonly rejectedProviders: readonly ProviderRejectionEvent[];
  public readonly unavailableProviders: readonly ProviderUnavailabilityEvent[];

  public constructor(
    message: string,
    rejectedProviders: readonly ProviderRejectionEvent[] = [],
    unavailableProviders: readonly ProviderUnavailabilityEvent[] = [],
  ) {
    super(message);
    this.name = "ProviderRouterError";
    this.code = "NO_ALLOWED_PROVIDER";
    this.rejectedProviders = rejectedProviders;
    this.unavailableProviders = unavailableProviders;
  }
}

export interface SovereignProviderRouterOptions {
  readonly providers: readonly LlmProvider[];
  readonly auditSink: AuditSink;
}

function toPolicyRequest(request: RouteRequest): RuntimePolicyRequest {
  return {
    classification: request.classification,
    requiresVision: request.requiresVision,
    requiresLongContext: request.requiresLongContext,
    requiresCodeGeneration: request.requiresCodeGeneration,
    humanApprovedCloudEgress: request.humanApprovedCloudEgress,
  };
}

function providerMap(providers: readonly LlmProvider[]): ReadonlyMap<ProviderId, LlmProvider> {
  const map = new Map<ProviderId, LlmProvider>();
  for (const provider of providers) {
    map.set(provider.id, provider);
  }
  return map;
}

export class SovereignProviderRouter {
  private readonly providers: ReadonlyMap<ProviderId, LlmProvider>;
  private readonly auditSink: AuditSink;

  public constructor(options: SovereignProviderRouterOptions) {
    this.providers = providerMap(options.providers);
    this.auditSink = options.auditSink;
  }

  public async route(request: RouteRequest): Promise<RouteDecision> {
    const rejectedProviders: ProviderRejectionEvent[] = [];
    const unavailableProviders: ProviderUnavailabilityEvent[] = [];
    let policy: RuntimePolicyDecision;

    try {
      policy = evaluateRuntimePolicy(toPolicyRequest(request));
    } catch (error: unknown) {
      if (error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER") {
        await this.auditNoAllowedProvider(request, rejectedProviders, unavailableProviders, error.message);
        throw new ProviderRouterError(error.message, rejectedProviders, unavailableProviders);
      }
      throw error;
    }

    const classificationDecision: AuditedClassificationDecision = {
      classification: request.classification,
      policy,
    };

    await this.auditSink.record({
      type: "classification_decision",
      tenantId: request.tenantId,
      traceId: request.traceId,
      payload: {
        classification: request.classification,
        providerOrder: policy.providerOrder,
        rejectedProviders: policy.rejectedProviders,
      },
      occurredAt: new Date().toISOString(),
    });

    for (const rejection of policy.rejectedProviders) {
      const event = { providerId: rejection.providerId, reason: rejection.reason };
      rejectedProviders.push(event);
      await this.auditSink.record({
        type: "provider_rejected",
        tenantId: request.tenantId,
        traceId: request.traceId,
        providerId: rejection.providerId,
        payload: { reason: rejection.reason },
        occurredAt: new Date().toISOString(),
      });
    }

    for (const providerId of policy.providerOrder) {
      const provider = this.providers.get(providerId);
      if (provider === undefined) {
        await this.recordUnavailable(request, unavailableProviders, providerId, "PROVIDER_NOT_REGISTERED");
        continue;
      }

      let available = false;
      try {
        available = await provider.isAvailable();
      } catch {
        await this.recordUnavailable(request, unavailableProviders, providerId, "PROVIDER_UNAVAILABLE");
        continue;
      }

      if (!available) {
        await this.recordUnavailable(request, unavailableProviders, providerId, "PROVIDER_UNAVAILABLE");
        continue;
      }

      try {
        const response = await provider.generate(request);
        await this.auditSink.record({
          type: "provider_selected",
          tenantId: request.tenantId,
          traceId: request.traceId,
          providerId,
          payload: { classification: request.classification },
          occurredAt: new Date().toISOString(),
        });
        return {
          providerId,
          response,
          classificationDecision,
          rejectedProviders,
          unavailableProviders,
        };
      } catch {
        await this.recordUnavailable(request, unavailableProviders, providerId, "PROVIDER_ERROR");
      }
    }

    await this.auditNoAllowedProvider(
      request,
      rejectedProviders,
      unavailableProviders,
      "NO_ALLOWED_PROVIDER: all policy-allowed providers were unavailable or failed",
    );
    throw new ProviderRouterError(
      "NO_ALLOWED_PROVIDER: all policy-allowed providers were unavailable or failed",
      rejectedProviders,
      unavailableProviders,
    );
  }

  private async recordUnavailable(
    request: RouteRequest,
    unavailableProviders: ProviderUnavailabilityEvent[],
    providerId: ProviderId,
    reason: ProviderUnavailabilityEvent["reason"],
  ): Promise<void> {
    unavailableProviders.push({ providerId, reason });
    await this.auditSink.record({
      type: "provider_unavailable",
      tenantId: request.tenantId,
      traceId: request.traceId,
      providerId,
      payload: { reason },
      occurredAt: new Date().toISOString(),
    });
  }

  private async auditNoAllowedProvider(
    request: RouteRequest,
    rejectedProviders: readonly ProviderRejectionEvent[],
    unavailableProviders: readonly ProviderUnavailabilityEvent[],
    reason: string,
  ): Promise<void> {
    await this.auditSink.record({
      type: "no_allowed_provider",
      tenantId: request.tenantId,
      traceId: request.traceId,
      payload: { reason, rejectedProviders, unavailableProviders },
      occurredAt: new Date().toISOString(),
    });
  }
}
