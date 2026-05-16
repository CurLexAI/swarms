export type Result<T, E> =
  | { ok: true; value: T }
  | { ok: false; error: E };

export interface AppInfo {
  id: string;
  name: string;
  createdAt: string;
}

export interface DeploymentInfo {
  id: string;
  appId: string;
  status: string;
  updatedAt: string;
}

export interface ModelEndpointInfo {
  endpointId: string;
  appId: string;
  url: string;
  model: string;
}

export interface ToolError {
  code: string;
  message: string;
}
