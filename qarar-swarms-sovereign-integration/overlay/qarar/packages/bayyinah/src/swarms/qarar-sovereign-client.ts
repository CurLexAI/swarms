import type { AppendOnlyFileAuditSink } from '../audit/append-only-file-sink.ts';
import { err, ok, type Result } from '../core/result.ts';
import { enforceSovereignOutput, type SourceReference } from '../contracts/sovereign-output.ts';
import { toUnifiedTransportEnvelope } from './protocol-adapter.ts';
import {
  validateQararSwarmsRequest,
  type QararSwarmsRequest,
  type QararSwarmsResponse,
  type QararSwarmsValidationError,
  type SwarmsProtocol
} from './sovereign-swarms-contract.ts';

export interface HttpResponseLike {
  readonly ok: boolean;
  readonly status: number;
  json(): Promise<unknown>;
  text(): Promise<string>;
}

export interface HttpRequestLike {
  readonly method: 'POST';
  readonly headers: Readonly<Record<string, string>>;
  readonly body: string;
  readonly signal?: AbortSignal;
}

export type HttpFetcher = (
  url: string,
  init: HttpRequestLike
) => Promise<HttpResponseLike>;

export interface QararSovereignClientOptions {
  readonly baseUrl: string;
  readonly token?: string;
  readonly timeoutMs: number;
  readonly fetcher?: HttpFetcher;
  readonly auditSink?: AppendOnlyFileAuditSink;
}

export interface QararSwarmsClientError {
  readonly code:
    | 'INVALID_BASE_URL'
    | 'VALIDATION_ERROR'
    | 'PROTOCOL_ERROR'
    | 'HTTP_ERROR'
    | 'RESPONSE_PARSE_ERROR'
    | 'FETCH_UNAVAILABLE'
    | 'REQUEST_FAILED';
  readonly message: string;
  readonly traceId: string;
  readonly status?: number;
}

interface RawQararResponse {
  readonly text: string;
  readonly confidence: number;
  readonly sources: readonly SourceReference[];
  readonly escalated?: boolean;
  readonly protocol?: SwarmsProtocol;
}

const isRecord = (value: unknown): value is Readonly<Record<string, unknown>> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isSourceReference = (value: unknown): value is SourceReference => {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.sourceId === 'string' &&
    typeof value.sourceType === 'string' &&
    typeof value.hash === 'string'
  );
};

const parseRawQararResponse = (
  value: unknown
): Result<RawQararResponse, string> => {
  if (!isRecord(value)) {
    return err('response is not an object');
  }

  if (typeof value.text !== 'string') {
    return err('response.text must be a string');
  }

  if (typeof value.confidence !== 'number') {
    return err('response.confidence must be a number');
  }

  if (!Array.isArray(value.sources) || !value.sources.every(isSourceReference)) {
    return err('response.sources must be SourceReference[]');
  }

  const protocol = value.protocol;
  const escalated = value.escalated;

  return ok({
    text: value.text,
    confidence: value.confidence,
    sources: value.sources,
    escalated: typeof escalated === 'boolean' ? escalated : undefined,
    protocol:
      protocol === 'ACP' || protocol === 'ANP' || protocol === 'MCP'
        ? protocol
        : undefined
  });
};

export class QararSovereignClient {
  private readonly baseUrl: string;
  private readonly token?: string;
  private readonly timeoutMs: number;
  private readonly fetcher?: HttpFetcher;
  private readonly auditSink?: AppendOnlyFileAuditSink;

  public constructor(options: QararSovereignClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.token = options.token;
    this.timeoutMs = options.timeoutMs;
    this.fetcher = options.fetcher;
    this.auditSink = options.auditSink;
  }

  public async complete(
    request: QararSwarmsRequest
  ): Promise<Result<QararSwarmsResponse, QararSwarmsClientError | QararSwarmsValidationError>> {
    if (this.baseUrl.trim().length === 0) {
      return err({
        code: 'INVALID_BASE_URL',
        message: 'Qarar API baseUrl must not be empty.',
        traceId: request.traceId
      });
    }

    const validation = validateQararSwarmsRequest(request);

    if (!validation.ok) {
      return err(validation.error);
    }

    const envelope = toUnifiedTransportEnvelope(validation.value);

    if (!envelope.ok) {
      return err({
        code: 'PROTOCOL_ERROR',
        message: envelope.error.message,
        traceId: request.traceId
      });
    }

    const fetcher = this.fetcher ?? this.resolveGlobalFetcher();

    if (fetcher === undefined) {
      return err({
        code: 'FETCH_UNAVAILABLE',
        message: 'No fetch implementation available for QararSovereignClient.',
        traceId: request.traceId
      });
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      await this.audit('swarms.request.created', request, envelope.value.protocol);

      const response = await fetcher(`${this.baseUrl}/api/sovereign/swarms/complete`, {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify(envelope.value),
        signal: controller.signal
      });

      if (!response.ok) {
        const body = await response.text();
        return err({
          code: 'HTTP_ERROR',
          message: `Qarar API returned HTTP ${response.status}: ${body.slice(0, 512)}`,
          traceId: request.traceId,
          status: response.status
        });
      }

      const parsed = parseRawQararResponse(await response.json());

      if (!parsed.ok) {
        return err({
          code: 'RESPONSE_PARSE_ERROR',
          message: parsed.error,
          traceId: request.traceId
        });
      }

      const enforced = enforceSovereignOutput({
        data: parsed.value.text,
        traceId: request.traceId,
        confidence: parsed.value.confidence,
        sources: parsed.value.sources
      });

      const result: QararSwarmsResponse = {
        traceId: request.traceId,
        agentId: request.agentId,
        modelId: request.modelId,
        protocol: parsed.value.protocol ?? envelope.value.protocol,
        text: enforced.data,
        confidence: enforced.confidence,
        sources: enforced.sources,
        escalated: parsed.value.escalated ?? enforced.escalated
      };

      await this.audit('swarms.response.accepted', request, result.protocol);
      return ok(result);
    } catch (error: unknown) {
      return err({
        code: 'REQUEST_FAILED',
        message: error instanceof Error ? error.message : 'Qarar request failed.',
        traceId: request.traceId
      });
    } finally {
      clearTimeout(timer);
    }
  }

  private headers(): Readonly<Record<string, string>> {
    const headers: Record<string, string> = {
      'content-type': 'application/json',
      accept: 'application/json'
    };

    if (this.token !== undefined && this.token.trim().length > 0) {
      headers.authorization = `Bearer ${this.token}`;
    }

    return headers;
  }

  private resolveGlobalFetcher(): HttpFetcher | undefined {
    const fetchCandidate: unknown = globalThis.fetch;

    if (typeof fetchCandidate !== 'function') {
      return undefined;
    }

    return async (url: string, init: HttpRequestLike): Promise<HttpResponseLike> => {
      const response = await fetchCandidate(url, init);
      return response as HttpResponseLike;
    };
  }

  private async audit(
    stage: string,
    request: QararSwarmsRequest,
    protocol: SwarmsProtocol
  ): Promise<void> {
    if (this.auditSink === undefined) {
      return;
    }

    await this.auditSink.append({
      traceId: request.traceId,
      agentId: request.agentId,
      stage,
      timestamp: new Date().toISOString(),
      payload: {
        modelId: request.modelId,
        taskType: request.taskType,
        protocol,
        dataClass: request.dataContext.dataClass,
        containsPII: request.dataContext.containsPII
      }
    });
  }
}
