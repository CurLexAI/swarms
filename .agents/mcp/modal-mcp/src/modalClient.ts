import { Config } from './config.js';
import { AppInfo, DeploymentInfo, ModelEndpointInfo, Result, ToolError } from './types.js';

class ModalClient {
  constructor(private readonly config: Config) {}

  private async getJson<T>(path: string): Promise<Result<T, ToolError>> {
    const response = await fetch(`${this.config.modalApiBaseUrl}${path}`, {
      headers: {
        Authorization: `Bearer ${this.config.modalApiToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      return {
        ok: false,
        error: { code: 'MODAL_API_ERROR', message: `Modal API returned ${response.status}` }
      };
    }

    const payload = (await response.json()) as T;
    return { ok: true, value: payload };
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

  runSafeInference(endpointId: string, prompt: string): Promise<Result<{ output: string }, ToolError>> {
    return this.getJson<{ output: string }>(`/v1/model-endpoints/${endpointId}/infer?safe=true&prompt=${encodeURIComponent(prompt)}`);
  }
}

export function newModalClient(config: Config): ModalClient {
  return new ModalClient(config);
}
