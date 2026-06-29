// SPDX-License-Identifier: MIT
// Licensed under MIT
/**
 * Deprecated compatibility adapter for legacy runtime policy imports.
 *
 * The canonical runtime policy lives in `src/policy/runtime-policy.ts`. This
 * module intentionally contains no independent provider registry or routing
 * order; it only translates legacy request names into the canonical policy.
 */

import {
  evaluateRuntimePolicy,
  RuntimePolicyError,
  type DataClassification,
  type ProviderId,
  type RuntimePolicyDecision as CanonicalRuntimePolicyDecision,
} from "./policy/runtime-policy.js";

export type { DataClassification } from "./policy/runtime-policy.js";

export type RuntimeMode =
  | "STANDARD"
  | "BURST"
  | "NOTEBOOK"
  | "COPILOT_CLOUD_AGENT"
  | "LEGACY_OPEN_CLOUD";

export type RuntimePurpose = "GENERAL" | "CI_SETUP";
export type RuntimeProvider = ProviderId;

export interface RuntimePolicyRequest {
  readonly dataClassification: Exclude<DataClassification, "SECRET">;
  readonly mode?: RuntimeMode;
  readonly purpose?: RuntimePurpose;
  readonly allowExternalProvider?: boolean;
  readonly allowNotebookRuntime?: boolean;
}

export interface RuntimePolicyDecision {
  readonly allowed: boolean;
  readonly providers: readonly RuntimeProvider[];
  readonly reason: string;
  readonly canonicalDecision?: CanonicalRuntimePolicyDecision;
}

export function selectRuntimeProviders(request: RuntimePolicyRequest): RuntimePolicyDecision {
  const mode = request.mode ?? "STANDARD";

  if (mode === "LEGACY_OPEN_CLOUD") {
    return blocked("LEGACY_OPEN_CLOUD runtime is retired and blocked by the canonical policy adapter.");
  }

  if (mode === "NOTEBOOK" && request.allowNotebookRuntime !== true) {
    return blocked("Notebook runtime requires explicit public experiment approval.");
  }

  if (mode === "COPILOT_CLOUD_AGENT" && request.purpose !== "CI_SETUP") {
    return blocked("Copilot cloud agent is limited to CI setup only.");
  }

  let canonicalDecision: CanonicalRuntimePolicyDecision;
  try {
    canonicalDecision = evaluateRuntimePolicy({
      classification: request.dataClassification,
      requiresCodeGeneration: mode === "COPILOT_CLOUD_AGENT",
      requiresLongContext: mode === "BURST" || mode === "COPILOT_CLOUD_AGENT",
      humanApprovedCloudEgress:
        request.allowExternalProvider === true ||
        (mode === "COPILOT_CLOUD_AGENT" && request.purpose === "CI_SETUP"),
    });
  } catch (error: unknown) {
    if (error instanceof RuntimePolicyError && error.code === "NO_ALLOWED_PROVIDER") {
      return blocked("Canonical local sovereign runtime policy returned no allowed provider.");
    }
    throw error;
  }

  const providers = canonicalDecision.providerOrder;

  if (providers.length === 0) {
    return blocked("Canonical runtime policy returned no providers after legacy compatibility filters.");
  }

  return {
    allowed: true,
    providers,
    reason: "Providers selected by canonical runtime policy via deprecated compatibility adapter.",
    canonicalDecision,
  };
}

function blocked(reason: string): RuntimePolicyDecision {
  return {
    allowed: false,
    providers: [],
    reason,
  };
}
