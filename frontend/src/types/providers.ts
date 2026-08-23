export type ProviderConnectionStatus = "disconnected" | "connecting" | "connected" | "error";
export type ConnectableAuthMethod = "api_key" | "oauth" | "local";

export interface ProviderConnection {
  id: number;
  providerId: string;
  authType: string;
  accountLabel: string;
  endpointUrl?: string;
  createdAt?: string;
  updatedAt?: string;
  status: ProviderConnectionStatus;
}

export interface SupportedProvider {
  id: string;
  name: string;
  description?: string;
  authMethods: string[];
  chatSupported: boolean;
}

export interface ProviderSummary extends SupportedProvider {
  status: ProviderConnectionStatus;
  connection?: ProviderConnection;
}

export interface ProviderModel {
  id: string;
  name?: string;
  providerId: string;
}

export interface ConnectProviderInput {
  providerId: string;
  authMethod: ConnectableAuthMethod;
  apiKey?: string;
  accountLabel?: string;
  serverUrl?: string;
}

export interface ProviderAuthorization {
  providerId: string;
  status: "connecting";
  attemptId: string;
  authorizationUrl: string;
}

export interface OAuthConnectionStatus {
  providerId: string;
  status: "connecting" | "connected" | "error";
  error?: string;
}
