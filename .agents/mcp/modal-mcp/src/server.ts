import { createServer, IncomingMessage, ServerResponse } from 'node:http';
import { loadConfig } from './config.js';
import { newModalClient } from './modalClient.js';
import { Result, ToolError } from './types.js';

type Json = Record<string, unknown>;

interface ToolCall {
  tool: string;
  args?: Json;
  explicitApproval?: boolean;
}

function json(res: ServerResponse, code: number, data: Json): void {
  res.statusCode = code;
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(data));
}

async function parseBody(req: IncomingMessage): Promise<Result<ToolCall, ToolError>> {
  const chunks: Uint8Array[] = [];
  for await (const chunk of req) {
    chunks.push(chunk as Uint8Array);
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  try {
    const parsed = JSON.parse(raw) as ToolCall;
    return { ok: true, value: parsed };
  } catch {
    return { ok: false, error: { code: 'BAD_REQUEST', message: 'Invalid JSON body' } };
  }
}

const cfg = loadConfig(process.env);
if (!cfg.ok) {
  throw new Error(cfg.error);
}

const modal = newModalClient(cfg.value);

const readOnlyTools = [
  'modal_list_apps',
  'modal_list_deployments',
  'modal_get_deployment_status',
  'modal_list_model_endpoints',
  'modal_get_recent_logs',
  'modal_run_safe_inference'
] as const;

const mutatingToolsList = [
  'modal_deploy',
  'modal_update_gpu',
  'modal_update_secrets',
  'modal_delete_app',
  'modal_change_endpoint'
] as const;

const mutatingTools = new Set<string>(mutatingToolsList);

const server = createServer(async (req, res) => {
  if (req.url === '/healthz' && req.method === 'GET') {
    return json(res, 200, { status: 'ok' });
  }

  if (req.url !== '/sse' || req.method !== 'POST') {
    return json(res, 404, { error: 'Not found' });
  }

  const auth = req.headers.authorization ?? '';
  if (auth !== `Bearer ${cfg.value.mcpBearerToken}`) {
    return json(res, 401, { error: 'Unauthorized' });
  }

  const body = await parseBody(req);
  if (!body.ok) {
    return json(res, 400, { error: body.error.message });
  }

  const { tool, args, explicitApproval } = body.value;

  if (mutatingTools.has(tool)) {
    if (!cfg.value.enableMutatingTools) {
      return json(res, 403, { error: 'Mutating tools disabled by policy' });
    }
    if (explicitApproval !== true) {
      return json(res, 403, { error: 'explicitApproval=true required for mutating tools' });
    }
    return json(res, 501, { error: 'Mutating tools scaffolded but not implemented' });
  }

  switch (tool) {
    case 'modal_list_tools':
      return json(res, 200, {
        ok: true,
        value: {
          readOnlyTools,
          mutatingTools: mutatingToolsList,
          mutatingToolsEnabled: cfg.value.enableMutatingTools
        }
      });
    case 'modal_list_apps':
      return json(res, 200, await modal.listApps());
    case 'modal_list_deployments':
      return json(res, 200, await modal.listDeployments());
    case 'modal_get_deployment_status': {
      const deploymentId = String(args?.deploymentId ?? '');
      return json(res, 200, await modal.getDeploymentStatus(deploymentId));
    }
    case 'modal_list_model_endpoints':
      return json(res, 200, await modal.listModelEndpoints());
    case 'modal_get_recent_logs': {
      const deploymentId = String(args?.deploymentId ?? '');
      const requested = Number(args?.limit ?? cfg.value.maxLogLines);
      const limit = Math.min(Math.max(1, requested), cfg.value.maxLogLines);
      return json(res, 200, await modal.getRecentLogs(deploymentId, limit));
    }
    case 'modal_run_safe_inference': {
      const endpointId = String(args?.endpointId ?? '');
      const prompt = String(args?.prompt ?? '');
      return json(res, 200, await modal.runSafeInference(endpointId, prompt));
    }
    default:
      return json(res, 400, { error: `Unknown tool: ${tool}` });
  }
});

const port = Number(process.env.PORT ?? '8787');
server.listen(port, () => {
  process.stdout.write(`modal-mcp listening on ${cfg.value.mcpBaseUrl} (port ${port})\n`);
});
