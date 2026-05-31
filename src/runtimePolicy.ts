export type DataClassification = "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED";

export type RuntimeMode =
  | "STANDARD"
  | "BURST"
  | "NOTEBOOK"
  | "COPILOT_CLOUD_AGENT"
  | "LEGACY_OPEN_CLOUD";

export type RuntimePurpose = "GENERAL" | "CI_SETUP";

export type RuntimeProvider =
  | "local_llama_cpp"
  | "local_ollama"
  | "modal_vllm"
  | "external_provider"
  | "notebook_public_experiment"
  | "copilot_ci_setup";

export interface RuntimePolicyRequest {
  readonly dataClassification: DataClassification;
  readonly mode?: RuntimeMode;
  readonly purpose?: RuntimePurpose;
  readonly allowExternalProvider?: boolean;
  readonly allowModalProvider?: boolean;
  readonly allowNotebookRuntime?: boolean;
}

export interface RuntimePolicyDecision {
  readonly allowed: boolean;
  readonly providers: readonly RuntimeProvider[];
  readonly reason: string;
}

const LOCAL_RESTRICTED_ORDER = ["local_llama_cpp"] as const satisfies readonly RuntimeProvider[];
const LOCAL_STANDARD_ORDER = ["local_ollama", "local_llama_cpp"] as const satisfies readonly RuntimeProvider[];

export function selectRuntimeProviders(request: RuntimePolicyRequest): RuntimePolicyDecision {
  const mode = request.mode ?? "STANDARD";

  if (mode === "LEGACY_OPEN_CLOUD") {
    return blocked("LEGACY_OPEN_CLOUD runtime is retired and blocked.");
  }

  if (request.dataClassification === "RESTRICTED" || request.dataClassification === "CONFIDENTIAL") {
    return {
      allowed: true,
      providers: LOCAL_RESTRICTED_ORDER,
      reason: "Restricted and confidential data are constrained to local-only providers.",
    };
  }

  if (mode === "NOTEBOOK") {
    if (request.dataClassification !== "PUBLIC" || !request.allowNotebookRuntime) {
      return blocked("Notebook runtime is limited to public experiment workloads only.");
    }

    return {
      allowed: true,
      providers: ["notebook_public_experiment"],
      reason: "Notebook runtime is allowed only for public experiment workloads.",
    };
  }

  if (mode === "COPILOT_CLOUD_AGENT") {
    if (request.purpose !== "CI_SETUP") {
      return blocked("Copilot cloud agent is limited to CI setup only.");
    }

    return {
      allowed: true,
      providers: ["copilot_ci_setup"],
      reason: "Copilot cloud agent is permitted only for CI setup.",
    };
  }

  const providers: RuntimeProvider[] = [...LOCAL_STANDARD_ORDER];

  if (request.allowModalProvider) {
    providers.push("modal_vllm");
  }

  if (mode === "BURST" && request.dataClassification === "PUBLIC" && request.allowExternalProvider) {
    providers.push("external_provider");
  }

  return {
    allowed: true,
    providers,
    reason: "Runtime providers selected by data classification and mode.",
  };
}

function blocked(reason: string): RuntimePolicyDecision {
  return {
    allowed: false,
    providers: [],
    reason,
  };
}
