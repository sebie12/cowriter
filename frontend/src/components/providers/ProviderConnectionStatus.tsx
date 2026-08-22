import type { ProviderConnectionStatus as ConnectionStatus } from "../../types/providers";

const statusLabels: Record<ConnectionStatus, string> = {
  disconnected: "Not connected",
  connecting: "Connecting",
  connected: "Connected",
  error: "Connection error",
};

interface ProviderConnectionStatusProps {
  status: ConnectionStatus;
}

export function ProviderConnectionStatus({ status }: ProviderConnectionStatusProps) {
  return (
    <span className={`provider-status provider-status-${status}`}>
      <span className="provider-status-dot" aria-hidden="true" />
      {statusLabels[status]}
    </span>
  );
}
