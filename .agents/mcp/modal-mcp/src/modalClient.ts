import { Config } from './config.js';
import { AppInfo, DeploymentInfo, ModelEndpointInfo, Result, ToolError } from './types.js';

class ModalClient {
  constructor(private readonly config: Config) {}

  private modalError(message: string): Result<never, ToolError> {
    return {
      ok: false,
      error: { code: 'MODAL_API_ERROR', message }
    };
  }

  private async parseJson<T>(response: Response): Promise<Result<T, ToolError>> {
    if (!response.ok) {
      return this.modalError(`Modal API returned ${response.status}`);
    }

    try {
      const payload = (await response.json()) as T;
      return { ok: true, value: payload };
    } catch {
      return this.modalError('Modal API returned invalid JSON');
    }
  }

  private async getJson<T>(path: string): Promise<Result<T, ToolError>> {
    try {
      const response = await fetch(`${this.config.modalApiBaseUrl}${path}`, {
        headers: {
          Authorization: `Bearer ${this.config.modalApiToken}`,
          'Content-Type': 'application/json'
        }
      });

      return this.parseJson<T>(response);
    } catch {
      return this.modalError('Modal API request failed');
    }
  }

  private async postJson<T>(path: string, body: unknown): Promise<Result<T, ToolError>> {
    try {
      const response = await fetch(`${this.config.modalApiBaseUrl}${path}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${this.config.modalApiToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      return this.parseJson<T>(response);
    } catch {
      return this.modalError('Modal API request failed');
    }
  }

  listApps(): Promise<Result<AppInfo[], ToolError>> {
    return this.getJson<AppInfo[]>('/v1/apps');
  }

  listDeployments(): Promise<Result<DeploymentInfo[], ToolError>> {
    return this.getJson<DeploymentInfo[]>('/v1/deployments');
  }

  getDeploymentStatus(deploymentId: string): Promise<Result<DeploymentInfo, ToolError>> {
    return this.getJson<DeploymentInfo>(`/v1/deployments/${deploymentId}`);
  }

  listModelEndpoints(): Promise<Result<ModelEndpointInfo[], ToolError>> {
    return this.getJson<ModelEndpointInfo[]>('/v1/model-endpoints');
  }

  getRecentLogs(deploymentId: string, limit: number): Promise<Result<string[], ToolError>> {
    return this.getJson<string[]>(`/v1/deployments/${deploymentId}/logs?limit=${limit}`);
  }

  // Prompt is sent in the POST body to avoid it appearing in server access logs.
  runSafeInference(endpointId: string, prompt: string): Promise<Result<{ output: string }, ToolError>> {
    return this.postJson<{ output: string }>(
      `/v1/model-endpoints/${endpointId}/infer`,
      { safe: true, prompt }
    );
  }
}

export function newModalClient(config: Config): ModalClient {
  return new ModalClient(config);
}
