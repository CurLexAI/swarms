export type HuggingFaceIntegrationMode = "disabled" | "offline_artifact_sync";

export interface HuggingFaceArtifactRequest {
  readonly modelRepo: string;
  readonly revision?: string;
  readonly localDir?: string;
}

export interface HuggingFaceArtifactDecision {
  readonly enabled: boolean;
  readonly mode: HuggingFaceIntegrationMode;
  readonly reason: string;
}

export interface HuggingFaceModelArtifactPort {
  evaluate(request: HuggingFaceArtifactRequest): Promise<HuggingFaceArtifactDecision>;
}

export interface HuggingFaceBoundaryConfig {
  readonly mode?: string;
  readonly modelRepo?: string;
  readonly token?: string;
  readonly hfHome?: string;
}

export class MockHuggingFaceArtifactAdapter implements HuggingFaceModelArtifactPort {
  constructor(private readonly decision: HuggingFaceArtifactDecision) {}

  async evaluate(_request: HuggingFaceArtifactRequest): Promise<HuggingFaceArtifactDecision> {
    return this.decision;
  }
}

export class OfflineHuggingFaceArtifactAdapter implements HuggingFaceModelArtifactPort {
  async evaluate(request: HuggingFaceArtifactRequest): Promise<HuggingFaceArtifactDecision> {
    const modelRepo = request.modelRepo.trim();
    if (modelRepo.length === 0) {
      return {
        enabled: false,
        mode: "disabled",
        reason: "CONFIG_NOT_FOUND: HF_MODEL_REPO must be a non-empty repository identifier before artifact sync review"
      };
    }

    return {
      enabled: false,
      mode: "disabled",
      reason: "OFFLINE_MODE: Hugging Face artifact synchronization is disabled by default"
    };
  }
}

export function createHuggingFaceArtifactPort(
  config: HuggingFaceBoundaryConfig = process.env
): HuggingFaceModelArtifactPort {
  const mode = config.mode ?? process.env.HF_INTEGRATION_MODE ?? "disabled";
  if (mode !== "disabled") {
    return new OfflineHuggingFaceArtifactAdapter();
  }

  return new OfflineHuggingFaceArtifactAdapter();
}

export function readHuggingFaceArtifactRequest(
  config: HuggingFaceBoundaryConfig = process.env
): HuggingFaceArtifactRequest {
  return {
    modelRepo: config.modelRepo ?? process.env.HF_MODEL_REPO ?? "",
    localDir: config.hfHome ?? process.env.HF_HOME
  };
}
