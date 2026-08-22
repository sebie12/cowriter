import type { ProviderSummary } from "../../types/providers";
import { ProviderList } from "./ProviderList";

interface ProvidersSettingsProps {
  providers: ProviderSummary[];
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  selectedProviderId: string | null;
  onRefresh: () => void;
  onSelectProvider: (provider: ProviderSummary) => void;
}

export function ProvidersSettings({
  providers,
  error,
  isLoading,
  isRefreshing,
  selectedProviderId,
  onRefresh,
  onSelectProvider,
}: ProvidersSettingsProps) {
  const connectedCount = providers.filter((provider) => provider.status === "connected").length;

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
