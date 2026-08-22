import type { ProviderSummary } from "../../types/providers";
import { ProviderListItem } from "./ProviderListItem";

interface ProviderListProps {
  providers: ProviderSummary[];
  selectedProviderId: string | null;
  onSelectProvider: (provider: ProviderSummary) => void;
}

export function ProviderList({ providers, selectedProviderId, onSelectProvider }: ProviderListProps) {
  if (providers.length === 0) {
    return (
      <section className="providers-empty-state" aria-label="No supported providers">
        <p className="eyebrow">No supported providers</p>
        <h2>No model providers available</h2>
        <p>The backend did not return any configured providers.</p>
      </section>
    );
  }

  return (
    <section className="provider-list" aria-label="AI providers">
      {providers.map((provider) => (
        <ProviderListItem
          key={provider.id}
          provider={provider}
          isSelected={selectedProviderId === provider.id}
          onConnect={() => onSelectProvider(provider)}
        />
      ))}
    </section>
  );
}
