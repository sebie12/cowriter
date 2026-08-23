import { useEffect, useRef, useState } from "react";
import type { UseProvidersState } from "../../hooks/useProviders";
import type { ProviderSummary } from "../../types/providers";
import { ProviderAuthPanel } from "../providers/ProviderAuthPanel";
import { ProvidersSettings } from "../providers/ProvidersSettings";
import { SettingsSidebar, type SettingsSection } from "./SettingsSidebar";

interface SettingsModalProps {
  providerState: UseProvidersState;
  activeConnectionId: number | null;
  selectionDisabled: boolean;
  onSelectActiveConnection: (connectionId: number) => void;
  onClose: () => void;
}

export function SettingsModal({
  providerState,
  activeConnectionId,
  selectionDisabled,
  onSelectActiveConnection,
  onClose,
}: SettingsModalProps) {
  const [selectedSection, setSelectedSection] = useState<SettingsSection>("model-providers");
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const {
    providers,
    connections,
    error,
    actionError,
    isLoading,
    isRefreshing,
    connectingProviderId,
    authorizationUrls,
    connectProvider,
    refreshProviders,
    cancelConnection,
    clearActionError,
    reopenAuthorization,
  } = providerState;
  const selectedProvider = providers.find((provider) => provider.id === editingProviderId) ?? null;

  const closeProviderPanel = () => {
    cancelConnection();
    clearActionError();
    setEditingProviderId(null);
  };

  const closeSettings = () => {
    cancelConnection();
    onClose();
  };

  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }

      if (editingProviderId) {
        closeProviderPanel();
      } else {
        closeSettings();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editingProviderId]);

  const selectProvider = (provider: ProviderSummary) => {
    clearActionError();
    setEditingProviderId(provider.id);
  };

  return (
    <div
      className="settings-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          closeSettings();
        }
      }}
    >
      <div className={`settings-stage ${selectedProvider ? "provider-open" : ""}`}>
        <section className="settings-panel" role="dialog" aria-modal={selectedProvider ? undefined : true} aria-labelledby="settings-title">
          <header className="settings-header">
            <div>
              <p className="eyebrow">Workspace</p>
              <h1 id="settings-title">Settings</h1>
            </div>
            <button ref={closeButtonRef} className="settings-close-button" type="button" onClick={closeSettings} aria-label="Close settings">
              <span aria-hidden="true">x</span>
            </button>
          </header>
          <div className="settings-layout">
            <SettingsSidebar selectedSection={selectedSection} onSelectSection={setSelectedSection} />
            <div className="settings-content">
              {selectedSection === "model-providers" && (
                <ProvidersSettings
                  providers={providers}
                  connections={connections}
                  activeConnectionId={activeConnectionId}
                  selectionDisabled={selectionDisabled}
                  error={error}
                  isLoading={isLoading}
                  isRefreshing={isRefreshing}
                  selectedProviderId={editingProviderId}
                  onRefresh={() => void refreshProviders()}
                  onSelectActiveConnection={onSelectActiveConnection}
                  onSelectProvider={selectProvider}
                />
              )}
            </div>
          </div>
        </section>

        {selectedProvider && (
          <ProviderAuthPanel
            key={selectedProvider.id}
            provider={selectedProvider}
            isConnecting={connectingProviderId === selectedProvider.id}
            authorizationUrl={authorizationUrls[selectedProvider.id] ?? null}
            error={actionError}
            onConnect={connectProvider}
            onClearError={clearActionError}
            onReopenAuthorization={() => void reopenAuthorization(selectedProvider.id)}
            onClose={closeProviderPanel}
          />
        )}
      </div>
    </div>
  );
}
