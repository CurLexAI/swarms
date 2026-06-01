import { decideEgress } from '../security/egress-policy.ts';
import { err, ok, type Result } from '../core/result.ts';
import type {
  QararSwarmsRequest,
  SwarmsProtocol
} from './sovereign-swarms-contract.ts';

export interface UnifiedTransportEnvelope {
  readonly schemaVersion: 'ute.v1';
  readonly traceId: string;
  readonly sourceAgentId: string;
  readonly targetModelId: string;
  readonly protocol: SwarmsProtocol;
  readonly payload: {
    readonly taskType: string;
    readonly prompt: string;
    readonly context: readonly {
      readonly key: string;
      readonly value: string;
    }[];
  };
  readonly controls: {
    readonly jurisdiction: 'KSA';
    readonly dataClass: string;
    readonly containsPII: boolean;
    readonly auditRequired: true;
    readonly retention: 'append-only';
  };
}

export interface ProtocolRouteDecision {
  readonly protocol: SwarmsProtocol;
  readonly reason:
    | 'PREFERRED_PROTOCOL'
    | 'ANP_FOR_REGULATED_OR_PII'
    | 'MCP_FOR_LOCAL_CONTEXT'
    | 'ACP_FOR_LOW_RISK_FAST_PATH';
}

export interface ProtocolAdapterError {
  readonly code:
    | 'EGRESS_DENIED'
    | 'UNSUPPORTED_PROTOCOL';
  readonly message: string;
}

const SUPPORTED_PROTOCOLS: readonly SwarmsProtocol[] = ['ACP', 'ANP', 'MCP'];

export const routeProtocol = (
  request: QararSwarmsRequest
): Result<ProtocolRouteDecision, ProtocolAdapterError> => {
  if (request.preferredProtocol !== undefined) {
    if (!SUPPORTED_PROTOCOLS.includes(request.preferredProtocol)) {
      return err({
        code: 'UNSUPPORTED_PROTOCOL',
        message: `unsupported protocol: ${request.preferredProtocol}`
      });
    }

    return ok({ protocol: request.preferredProtocol, reason: 'PREFERRED_PROTOCOL' });
  }

  if (request.dataContext.dataClass === 'REGULATED' || request.dataContext.containsPII) {
    return ok({ protocol: 'ANP', reason: 'ANP_FOR_REGULATED_OR_PII' });
  }

  if (request.taskType === 'LOCAL_CONTEXT') {
    return ok({ protocol: 'MCP', reason: 'MCP_FOR_LOCAL_CONTEXT' });
  }

  return ok({ protocol: 'ACP', reason: 'ACP_FOR_LOW_RISK_FAST_PATH' });
};

export const toUnifiedTransportEnvelope = (
  request: QararSwarmsRequest
): Result<UnifiedTransportEnvelope, ProtocolAdapterError> => {
  const egressDecision = decideEgress(request.dataContext, 'modal');

  if (!egressDecision.allowed) {
    return err({
      code: 'EGRESS_DENIED',
      message: egressDecision.message
    });
  }

  const route = routeProtocol(request);

  if (!route.ok) {
    return route;
  }

  return ok({
    schemaVersion: 'ute.v1',
    traceId: request.traceId,
    sourceAgentId: request.agentId,
    targetModelId: request.modelId,
    protocol: route.value.protocol,
    payload: {
      taskType: request.taskType,
      prompt: request.prompt,
      context: request.context.map((item) => ({
        key: item.key,
        value: item.value
      }))
    },
    controls: {
      jurisdiction: 'KSA',
      dataClass: request.dataContext.dataClass,
      containsPII: request.dataContext.containsPII,
      auditRequired: true,
      retention: 'append-only'
    }
  });
};
