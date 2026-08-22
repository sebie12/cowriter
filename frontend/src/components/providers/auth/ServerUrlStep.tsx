import { FormEvent, useState } from "react";

const DEFAULT_OLLAMA_SERVER_URL = "http://127.0.0.1:11434";

interface ServerUrlStepProps {
  isConnecting: boolean;
  initialServerUrl?: string;
  onBack: () => void;
  onSubmit: (serverUrl: string, accountLabel?: string) => Promise<void>;
}

function validateServerUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return "Use an HTTP or HTTPS URL.";
    }
    if (url.username || url.password) {
      return "Do not include credentials in the server URL.";
    }
    const hostname = url.hostname.toLowerCase();
    const ipv4Parts = hostname.split(".");
    const isIpv4Loopback = ipv4Parts.length === 4
      && ipv4Parts[0] === "127"
      && ipv4Parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) <= 255);
    if (hostname !== "localhost" && hostname !== "[::1]" && !isIpv4Loopback) {
      return "Use an Ollama server running on this computer.";
    }
    if (url.pathname !== "/" || url.search || url.hash) {
      return "Enter only the server address, without a path, query, or fragment.";
    }
  } catch {
    return "Enter a valid server URL.";
  }

  return null;
}

export function ServerUrlStep({ isConnecting, initialServerUrl, onBack, onSubmit }: ServerUrlStepProps) {
  const [serverUrl, setServerUrl] = useState(initialServerUrl ?? DEFAULT_OLLAMA_SERVER_URL);
  const [accountLabel, setAccountLabel] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isConnecting) {
      return;
    }

    const normalizedInput = serverUrl.trim();
    const nextError = validateServerUrl(normalizedInput);
    setValidationError(nextError);
    if (nextError) {
      return;
    }

    void onSubmit(normalizedInput, accountLabel.trim() || undefined);
  };

  return (
    <form className="auth-step auth-form" onSubmit={submit}>
      <div className="auth-step-heading">
        <span>Step 2 of 2</span>
        <h3>Connect to Ollama</h3>
        <p>Enter the address of the Ollama server running on this computer.</p>
      </div>

      <label>
        <span>Server URL</span>
        <input
          autoFocus
          type="url"
          value={serverUrl}
          placeholder={DEFAULT_OLLAMA_SERVER_URL}
          disabled={isConnecting}
          spellCheck={false}
          onChange={(event) => {
            setServerUrl(event.target.value);
            setValidationError(null);
          }}
        />
      </label>
      {validationError && <p className="auth-field-error" role="alert">{validationError}</p>}
      <p className="auth-field-note">Cowriter checks the Ollama server through its backend. No API key or other credential is sent.</p>

      <label>
        <span>Connection label <small>Optional</small></span>
        <input
          type="text"
          value={accountLabel}
          placeholder="Local Ollama"
          disabled={isConnecting}
          onChange={(event) => setAccountLabel(event.target.value)}
        />
      </label>

      <div className="auth-panel-actions">
        <button className="provider-secondary-button" type="button" disabled={isConnecting} onClick={onBack}>Back</button>
        <button className="provider-primary-button" type="submit" disabled={isConnecting || !serverUrl.trim()}>
          {isConnecting ? "Checking server..." : "Connect"}
        </button>
      </div>
    </form>
  );
}
