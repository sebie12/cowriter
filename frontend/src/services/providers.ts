import type { ConnectProviderInput, OAuthConnectionStatus, ProviderAuthorization, ProviderConnection, ProviderConnectionStatus, ProviderModel, SupportedProvider } from "../types/providers";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000";

interface ProviderConnectionResponse {
  id?: unknown;
  provider?: unknown;
  auth_method?: unknown;
  account_label?: unknown;
  endpoint_url?: unknown;
  status?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
}

interface SupportedProviderResponse {
  id?: unknown;
  name?: unknown;
  description?: unknown;
  auth_methods?: unknown;
  chat_supported?: unknown;
}

interface ProviderAuthorizationResponse {
  provider?: unknown;
  status?: unknown;
  attempt_id?: unknown;
  authorization_url?: unknown;
}

interface OAuthConnectionStatusResponse {
  provider?: unknown;
  status?: unknown;
  error?: unknown;
}

interface ProviderModelsResponse {
  provider?: unknown;
  models?: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeProviderId(value: string): string {
  return value.trim().toLowerCase().replace(/[\s-]+/g, "_");
}

function normalizeAuthMethod(value: string): string {
  const normalized = value.trim().toLowerCase().replace(/[\s.-]+/g, "_");
  if (["oauth", "oauth2", "oauth_2", "oauth_2_0"].includes(normalized)) {
    return "oauth";
  }
  if (["api_key", "apikey"].includes(normalized)) {
    return "api_key";
  }

  return normalized;
}

function normalizeStatus(value: unknown): ProviderConnectionStatus {
  if (value === "disconnected" || value === "connecting" || value === "connected" || value === "error") {
    return value;
  }

  return "disconnected";
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function normalizeProviderConnection(rawConnection: unknown): ProviderConnection {
  if (!isRecord(rawConnection)) {
    throw new Error("Backend returned an invalid provider connection.");
  }

  const connection = rawConnection as ProviderConnectionResponse;

  if (
    typeof connection.id !== "number" ||
    typeof connection.provider !== "string" ||
    typeof connection.auth_method !== "string" ||
    typeof connection.account_label !== "string"
  ) {
    throw new Error("Backend returned an invalid provider connection.");
  }

  return {
    id: connection.id,
    providerId: normalizeProviderId(connection.provider),
    authType: normalizeAuthMethod(connection.auth_method),
    accountLabel: connection.account_label,
    endpointUrl: typeof connection.endpoint_url === "string" ? connection.endpoint_url : undefined,
    createdAt: typeof connection.created_at === "string" ? connection.created_at : undefined,
    updatedAt: typeof connection.updated_at === "string" ? connection.updated_at : undefined,
    status: normalizeStatus(connection.status),
  };
}

function normalizeSupportedProvider(rawProvider: unknown): SupportedProvider {
  if (!isRecord(rawProvider)) {
    throw new Error("Backend returned an invalid provider.");
  }

  const provider = rawProvider as SupportedProviderResponse;

  if (typeof provider.id !== "string" || typeof provider.name !== "string") {
    throw new Error("Backend returned an invalid provider.");
  }

  return {
    id: normalizeProviderId(provider.id),
    name: provider.name,
    description: typeof provider.description === "string" ? provider.description : undefined,
    authMethods: Array.from(new Set(normalizeStringList(provider.auth_methods).map(normalizeAuthMethod))),
    chatSupported: provider.chat_supported === true,
  };
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    throw new Error("Could not reach the provider backend.");
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null) as { error?: unknown } | null;
    const message = typeof errorBody?.error === "string"
      ? errorBody.error
      : `Provider request failed with status ${response.status}.`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function fetchProviderConnections(signal?: AbortSignal): Promise<ProviderConnection[]> {
  const connections = await requestJson<unknown>("/provider-connections/", { signal });

  if (!Array.isArray(connections)) {
    throw new Error("Backend returned an invalid provider connection list.");
  }

  return connections.map(normalizeProviderConnection);
}

export async function fetchProviderModels(connectionId: number, signal?: AbortSignal): Promise<ProviderModel[]> {
  const response = await requestJson<unknown>(
    `/provider-connections/${encodeURIComponent(connectionId)}/models`,
    { signal },
  );
  if (!isRecord(response)) {
    throw new Error("Backend returned an invalid provider model list.");
  }

  const modelsResponse = response as ProviderModelsResponse;
  if (typeof modelsResponse.provider !== "string" || !Array.isArray(modelsResponse.models)) {
    throw new Error("Backend returned an invalid provider model list.");
  }

  const providerId = normalizeProviderId(modelsResponse.provider);
  return modelsResponse.models.map((model) => {
    if (!isRecord(model) || typeof model.id !== "string" || !model.id.trim()) {
      throw new Error("Backend returned an invalid provider model.");
    }
    return {
      id: model.id,
      name: typeof model.name === "string" ? model.name : undefined,
      providerId,
    };
  });
}

export async function fetchSupportedProviders(signal?: AbortSignal): Promise<SupportedProvider[]> {
  const providers = await requestJson<unknown>("/api/providers/", { signal });

  if (!Array.isArray(providers)) {
    throw new Error("Backend returned an invalid provider list.");
  }

  return providers.map(normalizeSupportedProvider);
}

export async function connectProvider(input: ConnectProviderInput, signal?: AbortSignal): Promise<ProviderConnection | ProviderAuthorization> {
  const response = await requestJson<unknown>(`/api/providers/${encodeURIComponent(input.providerId)}/connect`, {
    method: "POST",
    signal,
    body: JSON.stringify({
      auth_method: input.authMethod,
      api_key: input.apiKey,
      account_label: input.accountLabel,
      server_url: input.serverUrl,
    }),
  });

  if (isRecord(response)) {
    const authorization = response as ProviderAuthorizationResponse;
    if (
      authorization.status === "connecting" &&
      typeof authorization.provider === "string" &&
      typeof authorization.attempt_id === "string" &&
      typeof authorization.authorization_url === "string"
    ) {
      return {
        providerId: normalizeProviderId(authorization.provider),
        status: "connecting",
        attemptId: authorization.attempt_id,
        authorizationUrl: authorization.authorization_url,
      };
    }
  }

  return normalizeProviderConnection(response);
}

export async function fetchOAuthConnectionStatus(
  providerId: string,
  attemptId: string,
  signal?: AbortSignal,
): Promise<OAuthConnectionStatus> {
  const response = await requestJson<unknown>(
    `/api/providers/${encodeURIComponent(providerId)}/oauth/status/${encodeURIComponent(attemptId)}`,
    { signal },
  );
  if (!isRecord(response)) {
    throw new Error("Backend returned an invalid OAuth status.");
  }

  const statusResponse = response as OAuthConnectionStatusResponse;
  if (
    typeof statusResponse.provider !== "string" ||
    !["connecting", "connected", "error"].includes(String(statusResponse.status))
  ) {
    throw new Error("Backend returned an invalid OAuth status.");
  }

  return {
    providerId: normalizeProviderId(statusResponse.provider),
    status: statusResponse.status as OAuthConnectionStatus["status"],
    error: typeof statusResponse.error === "string" ? statusResponse.error : undefined,
  };
}
