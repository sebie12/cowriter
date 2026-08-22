import type { ConnectableAuthMethod } from "../types/providers";

export function isConnectableAuthMethod(method: string): method is ConnectableAuthMethod {
  return method === "api_key" || method === "oauth" || method === "local";
}
