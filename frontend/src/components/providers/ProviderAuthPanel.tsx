import { useState } from "react";
import type { ConnectableAuthMethod, ConnectProviderInput, ProviderSummary } from "../../types/providers";
import { ApiKeyStep } from "./auth/ApiKeyStep";
import { AuthMethodStep } from "./auth/AuthMethodStep";
import { OAuthStep } from "./auth/OAuthStep";
import { ServerUrlStep } from "./auth/ServerUrlStep";
import { CloseIcon } from "../ui/Icons";

interface ProviderAuthPanelProps {
  provider: ProviderSummary;
  isConnecting: boolean;
  authorizationUrl: string | null;
  error: string | null;
  onConnect: (input: ConnectProviderInput) => Promise<boolean>;
  onClearError: () => void;
  onClose: () => void;
  onReopenAuthorization: () => void;
}

type AuthStep = "method" | "credentials";

export function ProviderAuthPanel({
  provider,
  isConnecting,
  authorizationUrl,
  error,
  onConnect,
  onClearError,
  onClose,
  onReopenAuthorization,
}: ProviderAuthPanelProps) {
  const [step, setStep] = useState<AuthStep>("method");
  const [authMethod, setAuthMethod] = useState<ConnectableAuthMethod | null>(null);
  const [isOAuthWaiting, setIsOAuthWaiting] = useState(false);

  const submitConnection = async (input: Omit<ConnectProviderInput, "providerId" | "authMethod">) => {
    if (!authMethod) {
      return false;
    }

    const connected = await onConnect({ providerId: provider.id, authMethod, ...input });
    if (connected) {
      onClose();
    }
    return connected;
  };

  const startOAuth = async () => {
    setIsOAuthWaiting(true);
    const connected = await submitConnection({});
    if (!connected) {
      setIsOAuthWaiting(false);
    }
    return connected;
  };

  const goBack = () => {
    onClearError();
    setIsOAuthWaiting(false);
    setStep("method");
  };

  return (
    <aside className="provider-auth-panel" aria-labelledby="provider-auth-title">
      <header className="provider-auth-header">
        <div>
          <p className="eyebrow">Provider connection</p>
          <h2 id="provider-auth-title">{provider.connection ? "Configure" : "Connect"} {provider.name}</h2>
        </div>
        <button autoFocus className="settings-close-button" type="button" onClick={onClose} aria-label={`Close ${provider.name} connection panel`}>
          <CloseIcon />
        </button>
      </header>

      {error && (
        <div className="settings-error auth-error" role="alert">
          <strong>Connection failed.</strong> {error}
        </div>
      )}

      {step === "method" ? (
        <AuthMethodStep
          providerId={provider.id}
          authMethods={provider.authMethods}
          selectedMethod={authMethod}
          onSelectMethod={(method) => {
            onClearError();
            setAuthMethod(method);
          }}
          onContinue={() => authMethod && setStep("credentials")}
          onCancel={onClose}
        />
      ) : authMethod === "api_key" ? (
        <ApiKeyStep
          providerName={provider.name}
          isConnecting={isConnecting}
          onBack={goBack}
          onSubmit={async (apiKey, accountLabel) => {
            await submitConnection({ apiKey, accountLabel });
          }}
        />
      ) : authMethod === "oauth" ? (
        <OAuthStep
          providerName={provider.name}
          isConnecting={isConnecting}
          isWaiting={isOAuthWaiting}
          canReopenBrowser={Boolean(authorizationUrl)}
          onBack={goBack}
          onCancel={onClose}
          onReopenBrowser={onReopenAuthorization}
          onSignIn={startOAuth}
        />
      ) : authMethod === "local" ? (
        <ServerUrlStep
          isConnecting={isConnecting}
          initialServerUrl={provider.connection?.endpointUrl}
          onBack={goBack}
          onSubmit={async (serverUrl, accountLabel) => {
            await submitConnection({ serverUrl, accountLabel });
          }}
        />
      ) : null}
    </aside>
  );
}
