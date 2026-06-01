import { decideEgress, type LlmProvider } from '../security/egress-policy.ts';
import type { BayyinahDataContext } from '../contracts/data-classification.ts';

export interface BayyinahCompletionRequest {
  readonly traceId: string;
  readonly prompt: string;
  readonly provider: LlmProvider;
  readonly dataContext: BayyinahDataContext;
}

export interface BayyinahCompletionResponse {
  readonly traceId: string;
  readonly provider: LlmProvider;
  readonly text: string;
}

export interface BayyinahProviderClient {
  readonly name: LlmProvider;
  complete(request: BayyinahCompletionRequest): Promise<BayyinahCompletionResponse>;
}

export class BayyinahLLMError extends Error {
  public readonly providers: readonly string[];
  public readonly reasonCode: string;
  public readonly traceId: string;

  public constructor(message: string, providers: readonly string[], reasonCode: string, traceId: string) {
    super(message);
    this.name = 'BayyinahLLMError';
    this.providers = providers;
    this.reasonCode = reasonCode;
    this.traceId = traceId;
  }
}

export class BayyinahLLM {
  private readonly providers: ReadonlyMap<LlmProvider, BayyinahProviderClient>;

  public constructor(providers: readonly BayyinahProviderClient[]) {
    this.providers = new Map(providers.map((provider) => [provider.name, provider]));
  }

  public async complete(request: BayyinahCompletionRequest): Promise<BayyinahCompletionResponse> {
    const provider = this.providers.get(request.provider);

    if (provider === undefined) {
      throw new BayyinahLLMError(
        `Provider is not registered: ${request.provider}`,
        [request.provider],
        'PROVIDER_NOT_REGISTERED',
        request.traceId
      );
    }

    const egress = decideEgress(request.dataContext, provider.name);

    if (!egress.allowed) {
      throw new BayyinahLLMError(egress.message, [provider.name], egress.reasonCode, request.traceId);
    }

    return provider.complete(request);
  }
}
