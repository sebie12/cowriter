import { useEffect, useRef, useState } from "react";
import { openExternalUrl } from "../services/externalLinks";
import type { CowriterApi } from "../services/backend/types";
import type { ConnectProviderInput, ProviderConnection, ProviderSummary, SupportedProvider } from "../types/providers";

export interface UseProvidersState {
  providers: ProviderSummary[];
  connections: ProviderConnection[];
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  connectingProviderId: string | null;
  authorizationUrls: Record<string, string>;
  actionError: string | null;
  refreshVersion: number;
  connectProvider: (input: ConnectProviderInput) => Promise<boolean>;
  refreshProviders: () => Promise<void>;
  cancelConnection: () => void;
  clearActionError: () => void;
  reopenAuthorization: (providerId: string) => Promise<void>;
}

function messageFromError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Could not load provider connections.";
}

function providerNameFromId(providerId: string): string {
  return providerId
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function mergeProviders(
  supportedProviders: SupportedProvider[],
  connections: ProviderConnection[],
): ProviderSummary[] {
  const providersById = new Map<string, ProviderSummary>();

  supportedProviders.forEach((provider) => {
    providersById.set(provider.id, {
      id: provider.id,
      name: provider.name,
      description: provider.description,
      authMethods: provider.authMethods,
      chatSupported: provider.chatSupported,
      status: "disconnected",
    });
  });

  connections.forEach((connection) => {
    const provider = providersById.get(connection.providerId);

    if (provider) {
      providersById.set(connection.providerId, {
        ...provider,
        status: connection.status,
        connection,
      });
      return;
    }

    providersById.set(connection.providerId, {
      id: connection.providerId,
      name: providerNameFromId(connection.providerId),
      authMethods: connection.authType ? [connection.authType] : [],
      chatSupported: false,
      status: connection.status,
      connection,
    });
  });

  return Array.from(providersById.values()).sort((firstProvider, secondProvider) =>
    firstProvider.name.localeCompare(secondProvider.name),
  );
}

async function fetchProviderState(api: CowriterApi, signal?: AbortSignal): Promise<{
  providers: ProviderSummary[];
  connections: ProviderConnection[];
}> {
  const [supportedProviders, connections] = await Promise.all([
    api.listProviders(signal),
    api.listProviderConnections(signal),
  ]);

  return {
    providers: mergeProviders(supportedProviders, connections),
    connections,
  };
}

function wait(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Provider connection cancelled.", "AbortError"));
      return;
    }

    const handleAbort = () => {
      window.clearTimeout(timeoutId);
      reject(new DOMException("Provider connection cancelled.", "AbortError"));
    };
    const timeoutId = window.setTimeout(() => {
      signal.removeEventListener("abort", handleAbort);
      resolve();
    }, milliseconds);
    signal.addEventListener("abort", handleAbort, { once: true });
  });
}

function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}

export function useProviders(api: CowriterApi): UseProvidersState {
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [connections, setConnections] = useState<ProviderConnection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [connectingProviderId, setConnectingProviderId] = useState<string | null>(null);
  const [authorizationUrls, setAuthorizationUrls] = useState<Record<string, string>>({});
  const [refreshVersion, setRefreshVersion] = useState(0);
  const loadControllerRef = useRef<AbortController | null>(null);
  const connectionControllerRef = useRef<AbortController | null>(null);

  const loadProviders = async (refreshing = false) => {
    if (connectionControllerRef.current) {
      return;
    }
    loadControllerRef.current?.abort();
    const controller = new AbortController();
    loadControllerRef.current = controller;
    setError(null);
    setIsRefreshing(refreshing);
    setIsLoading(!refreshing);

    try {
      const nextState = await fetchProviderState(api, controller.signal);
      setProviders(nextState.providers);
      setConnections(nextState.connections);
      if (refreshing) {
        setRefreshVersion((version) => version + 1);
      }
    } catch (loadError) {
      if (!isAbortError(loadError)) {
        setError(messageFromError(loadError));
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  };

  const cancelConnection = () => {
    connectionControllerRef.current?.abort();
    connectionControllerRef.current = null;
    setConnectingProviderId(null);
    setAuthorizationUrls({});
    setProviders((currentProviders) => currentProviders.map((provider) =>
      provider.status === "connecting"
        ? { ...provider, status: provider.connection?.status ?? "disconnected" }
        : provider,
    ));
  };

  const connectProvider = async (input: ConnectProviderInput) => {
    cancelConnection();
    loadControllerRef.current?.abort();
    const controller = new AbortController();
    connectionControllerRef.current = controller;
    setActionError(null);
    setAuthorizationUrls({});
    setConnectingProviderId(input.providerId);
    setProviders((currentProviders) => currentProviders.map((provider) =>
      provider.id === input.providerId ? { ...provider, status: "connecting" } : provider,
    ));

    try {
      const result = await api.connectProvider(input, controller.signal);
      if ("authorizationUrl" in result) {
        setAuthorizationUrls({ [input.providerId]: result.authorizationUrl });
        setProviders((currentProviders) =>
          currentProviders.map((provider) =>
            provider.id === input.providerId
              ? { ...provider, status: "connecting" }
              : provider,
          ),
        );
        await openExternalUrl(result.authorizationUrl);

        for (let attempt = 0; attempt < 150; attempt += 1) {
          await wait(2000, controller.signal);
          const oauthStatus = await api.getOAuthConnectionStatus(
            input.providerId,
            result.attemptId,
            controller.signal,
          );
          if (oauthStatus.status === "connected") {
            const connections = await api.listProviderConnections(controller.signal);
            setAuthorizationUrls({});
            setProviders((currentProviders) => mergeProviders(currentProviders, connections));
            setConnections(connections);
            return true;
          }
          if (oauthStatus.status === "error") {
            throw new Error(oauthStatus.error ?? "The provider reported an authentication error. Start sign-in again to retry.");
          }
        }

        throw new Error("Provider sign-in is still pending. Complete it in your browser, then refresh providers.");
      }

      setProviders((currentProviders) => currentProviders.map((provider) =>
        provider.id === result.providerId
          ? { ...provider, status: result.status, connection: result }
          : provider,
      ));
      setConnections((currentConnections) => [
        ...currentConnections.filter((connection) => connection.id !== result.id),
        result,
      ]);
      return true;
    } catch (connectError) {
      if (!isAbortError(connectError)) {
        setActionError(messageFromError(connectError));
        setProviders((currentProviders) => currentProviders.map((provider) =>
          provider.id === input.providerId
            ? { ...provider, status: provider.connection?.status ?? "error" }
            : provider,
        ));
      }
      return false;
    } finally {
      if (connectionControllerRef.current === controller) {
        connectionControllerRef.current = null;
        setConnectingProviderId(null);
      }
    }
  };

  const reopenAuthorization = async (providerId: string) => {
    const authorizationUrl = authorizationUrls[providerId];
    if (!authorizationUrl) {
      return;
    }

    try {
      await openExternalUrl(authorizationUrl);
    } catch (openError) {
      setActionError(messageFromError(openError));
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    loadControllerRef.current = controller;

    const loadInitialProviders = async () => {
      setError(null);
      setIsLoading(true);

      try {
        const nextState = await fetchProviderState(api, controller.signal);
        setProviders(nextState.providers);
        setConnections(nextState.connections);
      } catch (loadError) {
        if (!isAbortError(loadError)) {
          setError(messageFromError(loadError));
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    void loadInitialProviders();

    return () => {
      controller.abort();
      connectionControllerRef.current?.abort();
    };
  }, [api]);

  return {
    providers,
    connections,
    error,
    actionError,
    refreshVersion,
    isLoading,
    isRefreshing,
    connectingProviderId,
    authorizationUrls,
    connectProvider,
    cancelConnection,
    clearActionError: () => setActionError(null),
    reopenAuthorization,
    refreshProviders: () => loadProviders(true),
  };
}
