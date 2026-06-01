import fs from "node:fs";
import path from "node:path";

export type ModelProvider = "ollama" | "modal" | "openai-compatible" | "local-file";

interface BaseModelEntry {
  id: string;
  provider: ModelProvider;
  model: string;
  profile: "local_only" | "sanitized_cloud" | "vision_local" | "code_local" | "human_review";
  use: string[];
}

export interface OllamaModelEntry extends BaseModelEntry {
  provider: "ollama";
  endpoint: string;
}

export interface ModalModelEntry extends BaseModelEntry {
  provider: "modal";
  app: string;
}

export interface OpenAICompatibleModelEntry extends BaseModelEntry {
  provider: "openai-compatible";
  baseUrlEnv: string;
  apiKeyEnv: string;
}

export interface LocalFileModelEntry extends BaseModelEntry {
  provider: "local-file";
  modelPath: string;
}

export type ModelEntry = OllamaModelEntry | ModalModelEntry | OpenAICompatibleModelEntry | LocalFileModelEntry;
export interface ModelRegistry { models: ModelEntry[] }

const PROVIDERS: readonly ModelProvider[] = ["ollama", "modal", "openai-compatible", "local-file"];

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readNonEmptyString(entry: Record<string, unknown>, key: string, idx: number): string {
  const value = entry[key];
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new Error(`models[${idx}].${key} must be a non-empty string`);
  }
  return value.trim();
}

function readUse(value: unknown, idx: number): string[] {
  if (!Array.isArray(value) || value.length === 0 || !value.every((v) => typeof v === "string" && v.trim())) {
    throw new Error(`models[${idx}].use must be a non-empty string array`);
  }
  return value.map((item) => item.trim());
}

function parseModelEntry(value: unknown, idx: number): ModelEntry {
  if (!isRecord(value)) throw new Error(`models[${idx}] must be an object`);
  const id = readNonEmptyString(value, "id", idx);
  const providerRaw = readNonEmptyString(value, "provider", idx);
  if (!PROVIDERS.includes(providerRaw as ModelProvider)) {
    throw new Error(`models[${idx}].provider must be one of ${PROVIDERS.join(", ")}`);
  }
  const provider = providerRaw as ModelProvider;
  const model = readNonEmptyString(value, "model", idx);
  const profile = readNonEmptyString(value, "profile", idx) as BaseModelEntry["profile"];
  const use = readUse(value.use, idx);

  if (provider === "ollama") {
    return { id, provider, model, profile, use, endpoint: readNonEmptyString(value, "endpoint", idx) };
  }
  if (provider === "modal") {
    return { id, provider, model, profile, use, app: readNonEmptyString(value, "app", idx) };
  }
  if (provider === "openai-compatible") {
    return {
      id,
      provider,
      model,
      profile,
      use,
      baseUrlEnv: readNonEmptyString(value, "baseUrlEnv", idx),
      apiKeyEnv: readNonEmptyString(value, "apiKeyEnv", idx)
    };
  }
  return { id, provider, model, profile, use, modelPath: readNonEmptyString(value, "modelPath", idx) };
}

export function loadModelRegistry(registryPath = path.resolve(process.cwd(), "config/models.registry.json")): ModelRegistry {
  if (!fs.existsSync(registryPath)) {
    throw new Error(`CONFIG_NOT_FOUND: model registry file missing at ${registryPath}`);
  }
  const parsed = JSON.parse(fs.readFileSync(registryPath, "utf8")) as unknown;
  if (!isRecord(parsed) || !Array.isArray(parsed.models)) {
    throw new Error("SYNTAX_FAILURE: registry must include a models array");
  }

  const models = parsed.models.map((entry, idx) => parseModelEntry(entry, idx));
  const dedup = new Set<string>();
  for (const model of models) {
    if (dedup.has(model.id)) throw new Error(`SYNTAX_FAILURE: duplicate model id ${model.id}`);
    dedup.add(model.id);
  }
  return { models };
}
