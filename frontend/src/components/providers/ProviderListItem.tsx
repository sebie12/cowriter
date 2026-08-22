import ollamaLogo from "../../assets/providers/ollama_icon.svg";
import type { ProviderSummary } from "../../types/providers";
import { isConnectableAuthMethod } from "../../utils/providerAuth";
import { ProviderConnectionStatus } from "./ProviderConnectionStatus";

interface ProviderListItemProps {
  provider: ProviderSummary;
  isSelected: boolean;
  onConnect: () => void;
}

const providerLogos: Partial<Record<string, string>> = {
  ollama: ollamaLogo,
};

function hasConnectableMethod(provider: ProviderSummary): boolean {
  return provider.authMethods.some((method) =>
    isConnectableAuthMethod(method) && (method !== "local" || provider.id === "ollama")
  );
}

export function ProviderListItem({ provider, isSelected, onConnect }: ProviderListItemProps) {
  const isConnected = provider.status === "connected";
  const canConnect = hasConnectableMethod(provider);
  const canConfigure = isConnected && provider.authMethods.includes("local");
  const providerLogo = providerLogos[provider.id];

  return (
    <article className={`provider-list-item ${isSelected ? "selected" : ""}`}>
      <div className="provider-logo-placeholder" aria-hidden="true">
        {providerLogo ? (
          <img className="provider-logo" src={providerLogo} alt="" />
        ) : (
          <span className="provider-logo-fallback" />
        )}
      </div>
      <div className="provider-list-item-copy">
        <h3>{provider.name}</h3>
        {isConnected && provider.connection ? (
          <p>{provider.connection.endpointUrl ?? provider.connection.accountLabel}</p>
        ) : (
          <p>{provider.description ?? "Connect this provider to use its models."}</p>
        )}
      </div>
      <div className="provider-list-item-actions">
        <ProviderConnectionStatus status={provider.status} />
        {(!isConnected || canConfigure) && (
          <button
            className="provider-primary-button"
            type="button"
            disabled={!canConnect || provider.status === "connecting"}
            title={canConnect ? undefined : "No supported connection flow is available."}
            onClick={onConnect}
          >
            {provider.status === "connecting" ? "Connecting..." : canConfigure ? "Configure" : canConnect ? "Connect" : "Unavailable"}
          </button>
        )}
      </div>
    </article>
  );
}
