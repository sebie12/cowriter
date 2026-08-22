interface ModelListProps {
  providerName: string;
}

export function ModelList({ providerName }: ModelListProps) {
  return (
    <section className="provider-models" aria-label={`${providerName} models`}>
      <div className="provider-section-heading">Available models</div>
      <p className="provider-muted">
        Model discovery is not available from the current backend API.
      </p>
    </section>
  );
}
