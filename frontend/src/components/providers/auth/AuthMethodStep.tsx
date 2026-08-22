import type { ConnectableAuthMethod } from "../../../types/providers";
import { isConnectableAuthMethod } from "../../../utils/providerAuth";

interface AuthMethodStepProps {
  providerId: string;
  authMethods: string[];
  selectedMethod: ConnectableAuthMethod | null;
  onSelectMethod: (method: ConnectableAuthMethod) => void;
  onContinue: () => void;
  onCancel: () => void;
}

function authMethodLabel(method: string): string {
  if (method === "api_key") {
    return "API key";
  }
  if (method === "oauth") {
    return "OAuth";
  }
  if (method === "local") {
    return "Local server";
  }

  return method
    .split("_")
    .filter(Boolean)
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

function authMethodDescription(method: ConnectableAuthMethod): string {
  if (method === "api_key") {
    return "Use a key created in your provider account.";
  }
  if (method === "oauth") {
    return "Continue in your system browser.";
  }
  return "Connect to an Ollama server on this computer. No credentials required.";
}

export function AuthMethodStep({ providerId, authMethods, selectedMethod, onSelectMethod, onContinue, onCancel }: AuthMethodStepProps) {
  return (
    <div className="auth-step">
      <div className="auth-step-heading">
        <span>Step 1 of 2</span>
        <h3>Choose a connection method</h3>
        <p>Select one of the connection methods configured for this provider.</p>
      </div>

      <div className="auth-method-list" role="radiogroup" aria-label="Connection method">
        {authMethods.map((method) => {
          const connectable = isConnectableAuthMethod(method) && (method !== "local" || providerId === "ollama");
          return (
            <label className={`auth-method-option ${!connectable ? "unavailable" : ""}`} key={method}>
              <input
                type="radio"
                name="auth-method"
                value={method}
                checked={selectedMethod === method}
                disabled={!connectable}
                onChange={() => connectable && onSelectMethod(method)}
              />
              <span>
                <strong>{authMethodLabel(method)}</strong>
                <small>{connectable ? authMethodDescription(method) : "This flow is not available in the app."}</small>
              </span>
            </label>
          );
        })}
      </div>

      <div className="auth-panel-actions">
        <button className="provider-secondary-button" type="button" onClick={onCancel}>Cancel</button>
        <button className="provider-primary-button" type="button" disabled={!selectedMethod} onClick={onContinue}>Continue</button>
      </div>
    </div>
  );
}
