import { createServer, IncomingMessage, ServerResponse } from 'node:http';
import { timingSafeEqual } from 'node:crypto';
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

// Constant-time comparison prevents timing-based token oracle attacks.
function authIsValid(header: string, token: string): boolean {
  const expected = Buffer.from(`Bearer ${token}`, 'utf8');
  const actual   = Buffer.from(header, 'utf8');
  if (expected.length !== actual.length) return false;
  return timingSafeEqual(expected, actual);
}

// Allow only safe alphanumeric IDs from caller-supplied args.
// Rejects path-traversal attempts like `../other` or URL-encoded variants.
const SAFE_ID_RE = /^[a-zA-Z0-9_-]{1,128}$/;
function validateId(raw: unknown, field: string): Result<string, ToolError> {
  const s = String(raw ?? '');
  if (!SAFE_ID_RE.test(s)) {
    return { ok: false, error: { code: 'INVALID_ARG', message: `${field} must match [a-zA-Z0-9_-]{1,128}` } };
  }
  return { ok: true, value: s };
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

  if (!authIsValid(req.headers.authorization ?? '', cfg.value.mcpBearerToken)) {
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
      const id = validateId(args?.deploymentId, 'deploymentId');
      if (!id.ok) return json(res, 400, { error: id.error.message });
      return json(res, 200, await modal.getDeploymentStatus(id.value));
    }
    case 'modal_list_model_endpoints':
      return json(res, 200, await modal.listModelEndpoints());
    case 'modal_get_recent_logs': {
      const id = validateId(args?.deploymentId, 'deploymentId');
      if (!id.ok) return json(res, 400, { error: id.error.message });
      const requested = Number(args?.limit ?? cfg.value.maxLogLines);
      const limit = Math.min(Math.max(1, requested), cfg.value.maxLogLines);
      return json(res, 200, await modal.getRecentLogs(id.value, limit));
    }
    case 'modal_run_safe_inference': {
      const id = validateId(args?.endpointId, 'endpointId');
      if (!id.ok) return json(res, 400, { error: id.error.message });
      const prompt = String(args?.prompt ?? '');
      return json(res, 200, await modal.runSafeInference(id.value, prompt));
    }
    default:
      return json(res, 400, { error: `Unknown tool: ${tool}` });
  }
});

const port = Number(process.env.PORT ?? '8787');
server.listen(port, () => {
  process.stdout.write(`modal-mcp listening on ${cfg.value.mcpBaseUrl} (port ${port})\n`);
});
