// SPDX-License-Identifier: MIT
// Licensed under MIT

export type DataClassification =
  | "PUBLIC"
  | "INTERNAL"
  | "CONFIDENTIAL"
  | "RESTRICTED"
  | "SECRET";

export type TrustBoundary =
  | "LOCAL_CONTROL_PLANE"
  | "SOVEREIGN_CLOUD"
  | "APPROVED_CLOUD"
  | "EXTERNAL_CLOUD";

export type RuntimeCapability =
  | "text_generation"
  | "code_generation"
  | "long_context"
  | "vision"
  | "local_inference"
  | "cloud_inference";

export type ProviderId =
  | "ollama-qwen-local"
  | "ollama-deepseek-local"
  | "modal-mihwar"
  | "modal-bayyinah"
  | "vertex-llama4"
  | "cursor-cloud";

export type LocalProviderId = "ollama-qwen-local" | "ollama-deepseek-local";

export type RuntimeArchitecture =
  | "node_express_primary"
  | "fastapi_primary_gateway"
  | "factory_driven_main_py"
  | "public_llm_gateway";

export interface CopilotCiPolicy {
  readonly mode: "setup_only" | "runtime_activation";
  readonly noSecretsMode: boolean;
  readonly liveProviderCallsAllowed: boolean;
  readonly allowedPurpose: "prepare_offline_mcp_environment";
}

export interface RuntimePolicyConfig {
  readonly primaryArchitecture: RuntimeArchitecture;
  readonly blockedLegacyArchitectures: readonly RuntimeArchitecture[];
  readonly copilotCi: CopilotCiPolicy;
}

export interface ProviderRegistryEntry {
  readonly id: ProviderId;
  readonly displayName: string;
  readonly trustBoundary: TrustBoundary;
  readonly capabilities: readonly RuntimeCapability[];
  readonly allowedClassifications: readonly DataClassification[];
  readonly requiresHumanReview: boolean;
}

export interface RuntimePolicyRequest {
  readonly classification: DataClassification;
  readonly requiresVision?: boolean;
  readonly requiresLongContext?: boolean;
  readonly requiresCodeGeneration?: boolean;
  readonly humanApprovedCloudEgress?: boolean;
}

export interface ProviderRejection {
  readonly providerId: ProviderId;
  readonly reason: RuntimePolicyRejectionCode;
}

export type RuntimePolicyRejectionCode =
  | "CLASSIFICATION_NOT_ALLOWED"
  | "CAPABILITY_NOT_SUPPORTED"
  | "HUMAN_REVIEW_REQUIRED"
  | "UNTRUSTED_BOUNDARY";

export interface RuntimePolicyDecision {
  readonly allowed: boolean;
  readonly classification: DataClassification;
  readonly requiredCapabilities: readonly RuntimeCapability[];
  readonly providerOrder: readonly ProviderId[];
  readonly rejectedProviders: readonly ProviderRejection[];
}

export type RuntimePolicyErrorCode = "INVALID_CLASSIFICATION" | "NO_ALLOWED_PROVIDER";

export class RuntimePolicyError extends Error {
  public readonly code: RuntimePolicyErrorCode;

  public constructor(code: RuntimePolicyErrorCode, message: string) {
    super(message);
    this.name = "RuntimePolicyError";
    this.code = code;
  }
}

const DATA_CLASSIFICATIONS: ReadonlySet<DataClassification> = new Set([
  "PUBLIC",
  "INTERNAL",
  "CONFIDENTIAL",
  "RESTRICTED",
  "SECRET",
]);

export const LOCAL_PROVIDER_IDS = [
  "ollama-qwen-local",
  "ollama-deepseek-local",
] as const satisfies readonly ProviderId[];

export const EXTERNAL_PROVIDER_IDS = [
  "vertex-llama4",
  "cursor-cloud",
] as const satisfies readonly ProviderId[];

export const runtimePolicy: RuntimePolicyConfig = {
  primaryArchitecture: "node_express_primary",
  blockedLegacyArchitectures: [
    "fastapi_primary_gateway",
    "factory_driven_main_py",
    "public_llm_gateway",
  ],
  copilotCi: {
    mode: "setup_only",
    noSecretsMode: true,
    liveProviderCallsAllowed: false,
    allowedPurpose: "prepare_offline_mcp_environment",
  },
} as const;

export const providerRegistry: Readonly<Record<ProviderId, ProviderRegistryEntry>> = {
  "ollama-qwen-local": {
    id: "ollama-qwen-local",
    displayName: "Ollama Qwen Local",
    trustBoundary: "LOCAL_CONTROL_PLANE",
    capabilities: ["text_generation", "code_generation", "local_inference"],
    allowedClassifications: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET"],
    requiresHumanReview: false,
  },
  "ollama-deepseek-local": {
    id: "ollama-deepseek-local",
    displayName: "Ollama DeepSeek Local",
    trustBoundary: "LOCAL_CONTROL_PLANE",
    capabilities: ["text_generation", "code_generation", "local_inference"],
    allowedClassifications: ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET"],
    requiresHumanReview: false,
  },
  "modal-mihwar": {
    id: "modal-mihwar",
    displayName: "Mihwar Sovereign Modal Runtime",
    trustBoundary: "SOVEREIGN_CLOUD",
    capabilities: ["text_generation", "code_generation", "long_context", "cloud_inference"],
    allowedClassifications: ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
    requiresHumanReview: false,
  },
  "modal-bayyinah": {
    id: "modal-bayyinah",
    displayName: "Bayyinah Sovereign Modal Runtime",
    trustBoundary: "SOVEREIGN_CLOUD",
    capabilities: ["text_generation", "code_generation", "long_context", "cloud_inference"],
    allowedClassifications: ["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
    requiresHumanReview: false,
  },
  "vertex-llama4": {
    id: "vertex-llama4",
    displayName: "Vertex Llama 4 Approved Cloud",
    trustBoundary: "APPROVED_CLOUD",
    capabilities: ["text_generation", "long_context", "vision", "cloud_inference"],
    allowedClassifications: ["PUBLIC", "INTERNAL"],
    requiresHumanReview: true,
  },
  "cursor-cloud": {
    id: "cursor-cloud",
    displayName: "Cursor Cloud Coding Agent",
    trustBoundary: "EXTERNAL_CLOUD",
    capabilities: ["text_generation", "code_generation", "long_context", "cloud_inference"],
    allowedClassifications: ["PUBLIC"],
    requiresHumanReview: true,
  },
} as const;

export const currentProviderOrder: readonly ProviderId[] = [
  "ollama-qwen-local",
  "ollama-deepseek-local",
  "modal-mihwar",
  "modal-bayyinah",
  "vertex-llama4",
  "cursor-cloud",
];

export function isLegacyArchitectureBlocked(
  architecture: RuntimeArchitecture,
  policy: RuntimePolicyConfig = runtimePolicy,
): boolean {
  return policy.blockedLegacyArchitectures.includes(architecture);
}

export function isLocalProvider(providerId: ProviderId): providerId is LocalProviderId {
  return (LOCAL_PROVIDER_IDS as readonly string[]).includes(providerId);
}

export function isRestrictedRouteLocalOnly(decision?: RuntimePolicyDecision): boolean {
  if (decision !== undefined) {
    return decision.classification === "RESTRICTED" && decision.providerOrder.every(isLocalProvider);
  }

  return currentProviderOrder
    .filter((providerId) => providerRegistry[providerId].allowedClassifications.includes("RESTRICTED"))
    .every(isLocalProvider);
}

export function isCopilotCiSetupOnly(policy: RuntimePolicyConfig = runtimePolicy): boolean {
  return (
    policy.copilotCi.mode === "setup_only" &&
    policy.copilotCi.noSecretsMode &&
    !policy.copilotCi.liveProviderCallsAllowed &&
    policy.copilotCi.allowedPurpose === "prepare_offline_mcp_environment"
  );
}

function assertClassification(value: DataClassification): void {
  if (!DATA_CLASSIFICATIONS.has(value)) {
    throw new RuntimePolicyError(
      "INVALID_CLASSIFICATION",
      "runtime policy classification is not recognized",
    );
  }
}

function requiredCapabilitiesFor(request: RuntimePolicyRequest): readonly RuntimeCapability[] {
  const capabilities: RuntimeCapability[] = ["text_generation"];
  if (request.requiresCodeGeneration === true) capabilities.push("code_generation");
  if (request.requiresLongContext === true) capabilities.push("long_context");
  if (request.requiresVision === true) capabilities.push("vision");
  return capabilities;
}

function rejectProvider(
  entry: ProviderRegistryEntry,
  request: RuntimePolicyRequest,
  requiredCapabilities: readonly RuntimeCapability[],
): RuntimePolicyRejectionCode | null {
  if (!entry.allowedClassifications.includes(request.classification)) {
    return "CLASSIFICATION_NOT_ALLOWED";
  }
  if (!requiredCapabilities.every((capability) => entry.capabilities.includes(capability))) {
    return "CAPABILITY_NOT_SUPPORTED";
  }
  if (entry.trustBoundary === "EXTERNAL_CLOUD" && request.classification !== "PUBLIC") {
    return "UNTRUSTED_BOUNDARY";
  }
  if (entry.requiresHumanReview && request.humanApprovedCloudEgress !== true) {
    return "HUMAN_REVIEW_REQUIRED";
  }
  return null;
}

export function evaluateRuntimePolicy(request: RuntimePolicyRequest): RuntimePolicyDecision {
  assertClassification(request.classification);

  const requiredCapabilities = requiredCapabilitiesFor(request);
  const providerOrder: ProviderId[] = [];
  const rejectedProviders: ProviderRejection[] = [];

  for (const providerId of currentProviderOrder) {
    const entry = providerRegistry[providerId];
    const rejection = rejectProvider(entry, request, requiredCapabilities);
    if (rejection === null) {
      providerOrder.push(providerId);
    } else {
      rejectedProviders.push({ providerId, reason: rejection });
    }
  }

  if (providerOrder.length === 0) {
    throw new RuntimePolicyError(
      "NO_ALLOWED_PROVIDER",
      "runtime policy failed closed because no provider is allowed for this request",
    );
  }

  return {
    allowed: true,
    classification: request.classification,
    requiredCapabilities,
    providerOrder,
    rejectedProviders,
  };
}
