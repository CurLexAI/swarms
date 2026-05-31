export const LOCAL_OLLAMA_PROVIDER = "local_ollama" as const;
export const LOCAL_LLAMA_CPP_PROVIDER = "local_llama_cpp" as const;

export const LOCAL_PROVIDER_IDS = [
  LOCAL_OLLAMA_PROVIDER,
  LOCAL_LLAMA_CPP_PROVIDER,
] as const;

export const EXTERNAL_PROVIDER_IDS = [
  "cursor_cloud",
  "vertex_llama4",
  "openai",
  "anthropic",
] as const;

export type LocalProviderId = (typeof LOCAL_PROVIDER_IDS)[number];
export type ExternalProviderId = (typeof EXTERNAL_PROVIDER_IDS)[number];
export type ProviderId = LocalProviderId | ExternalProviderId;

export type RuntimeArchitecture =
  | "node_express_primary"
  | "fastapi_primary_gateway"
  | "factory_driven_main_py"
  | "public_llm_gateway";

export type DataClassification =
  | "PUBLIC"
  | "INTERNAL"
  | "CONFIDENTIAL"
  | "RESTRICTED";

export type CopilotCiMode = "setup_only" | "runtime_activation";

export interface CopilotCiPolicy {
  readonly mode: CopilotCiMode;
  readonly noSecretsMode: boolean;
  readonly liveProviderCallsAllowed: boolean;
  readonly allowedPurpose: "prepare_offline_mcp_environment";
}

export interface RuntimePolicy {
  readonly primaryArchitecture: RuntimeArchitecture;
  readonly blockedLegacyArchitectures: readonly RuntimeArchitecture[];
  readonly providerOrderByClassification: Readonly<
    Record<DataClassification, readonly LocalProviderId[]>
  >;
  readonly copilotCi: CopilotCiPolicy;
}

export const runtimePolicy: RuntimePolicy = {
  primaryArchitecture: "node_express_primary",
  blockedLegacyArchitectures: [
    "fastapi_primary_gateway",
    "factory_driven_main_py",
    "public_llm_gateway",
  ],
  providerOrderByClassification: {
    PUBLIC: [LOCAL_OLLAMA_PROVIDER, LOCAL_LLAMA_CPP_PROVIDER],
    INTERNAL: [LOCAL_OLLAMA_PROVIDER, LOCAL_LLAMA_CPP_PROVIDER],
    CONFIDENTIAL: [LOCAL_LLAMA_CPP_PROVIDER],
    RESTRICTED: [LOCAL_LLAMA_CPP_PROVIDER],
  },
  copilotCi: {
    mode: "setup_only",
    noSecretsMode: true,
    liveProviderCallsAllowed: false,
    allowedPurpose: "prepare_offline_mcp_environment",
  },
} as const;

export function isLegacyArchitectureBlocked(
  architecture: RuntimeArchitecture,
  policy: RuntimePolicy = runtimePolicy,
): boolean {
  return policy.blockedLegacyArchitectures.includes(architecture);
}

export function providerOrderForClassification(
  classification: DataClassification,
  policy: RuntimePolicy = runtimePolicy,
): readonly LocalProviderId[] {
  return policy.providerOrderByClassification[classification];
}

export function isLocalProvider(providerId: ProviderId): providerId is LocalProviderId {
  return (LOCAL_PROVIDER_IDS as readonly string[]).includes(providerId);
}

export function isRestrictedRouteLocalOnly(
  policy: RuntimePolicy = runtimePolicy,
): boolean {
  return providerOrderForClassification("RESTRICTED", policy).every(isLocalProvider);
}

export function isCopilotCiSetupOnly(policy: RuntimePolicy = runtimePolicy): boolean {
  return (
    policy.copilotCi.mode === "setup_only" &&
    policy.copilotCi.noSecretsMode &&
    !policy.copilotCi.liveProviderCallsAllowed &&
    policy.copilotCi.allowedPurpose === "prepare_offline_mcp_environment"
  );
}
