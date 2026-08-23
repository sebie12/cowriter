import type { ProviderConnection, ProviderSummary } from "../../types/providers";
import { ProviderList } from "./ProviderList";

interface ProvidersSettingsProps {
  providers: ProviderSummary[];
  connections: ProviderConnection[];
  activeConnectionId: number | null;
  selectionDisabled: boolean;
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  selectedProviderId: string | null;
  onRefresh: () => void;
  onSelectActiveConnection: (connectionId: number) => void;
  onSelectProvider: (provider: ProviderSummary) => void;
}

export function ProvidersSettings({
  providers,
  connections,
  activeConnectionId,
  selectionDisabled,
  error,
  isLoading,
  isRefreshing,
  selectedProviderId,
  onRefresh,
  onSelectActiveConnection,
  onSelectProvider,
}: ProvidersSettingsProps) {
  const connectedCount = providers.filter((provider) => provider.status === "connected").length;
  const chatConnections = connections
    .filter((connection) => (
      connection.status === "connected"
      && providers.some((provider) => provider.id === connection.providerId && provider.chatSupported)
    ))
    .sort((firstConnection, secondConnection) => firstConnection.id - secondConnection.id);

  const connectionLabel = (connection: ProviderConnection) => {
    const providerName = providers.find((provider) => provider.id === connection.providerId)?.name ?? connection.providerId;
    return `${providerName} - ${connection.accountLabel}`;
  };

  return (
    <section className="providers-settings" aria-labelledby="providers-settings-title">
      <div className="settings-content-header">
        <div>
          <p className="eyebrow">Connections</p>
          <h2 id="providers-settings-title">Model Providers</h2>
          <p>Connect the providers you want Cowriter to use.</p>
        </div>
        <button className="provider-secondary-button" type="button" disabled={isLoading || isRefreshing} onClick={onRefresh}>
          {isRefreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="settings-error" role="alert">
          <strong>Could not load providers.</strong> {error}
        </div>
      )}

      <div className="active-provider-setting">
        <div>
          <label htmlFor="active-provider">Active chat provider</label>
          <p>Choose which connected provider Cowriter uses for chat.</p>
        </div>
        <select
          id="active-provider"
          value={activeConnectionId ?? ""}
          disabled={selectionDisabled || chatConnections.length === 0}
          onChange={(event) => onSelectActiveConnection(Number(event.target.value))}
        >
          {activeConnectionId === null && chatConnections.length > 0 && (
            <option value="" disabled>Select a provider</option>
          )}
          {chatConnections.length === 0 && <option value="">No chat providers connected</option>}
          {chatConnections.map((connection) => (
            <option key={connection.id} value={connection.id}>{connectionLabel(connection)}</option>
          ))}
        </select>
      </div>

      <div className="providers-summary">
        <span>{providers.length} available</span>
        <span>{connectedCount} connected</span>
      </div>

      {isLoading ? (
        <div className="providers-loading" role="status">Loading providers...</div>
      ) : (
        <ProviderList providers={providers} selectedProviderId={selectedProviderId} onSelectProvider={onSelectProvider} />
      )}
    </section>
  );
}
