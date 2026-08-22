import { FormEvent, useState } from "react";

interface ApiKeyStepProps {
  providerName: string;
  isConnecting: boolean;
  onBack: () => void;
  onSubmit: (apiKey: string, accountLabel?: string) => Promise<void>;
}

export function ApiKeyStep({ providerName, isConnecting, onBack, onSubmit }: ApiKeyStepProps) {
  const [apiKey, setApiKey] = useState("");
  const [accountLabel, setAccountLabel] = useState("");

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const submittedKey = apiKey.trim();
    if (!submittedKey || isConnecting) {
      return;
    }

    setApiKey("");
    void onSubmit(submittedKey, accountLabel.trim() || undefined);
  };

  return (
    <form className="auth-step auth-form" onSubmit={submit}>
      <div className="auth-step-heading">
        <span>Step 2 of 2</span>
        <h3>Enter your API key</h3>
        <p>The key is sent directly to the Cowriter backend and is not saved in frontend storage.</p>
      </div>

      <label>
        <span>API key</span>
        <input
          autoFocus
          autoComplete="off"
          type="password"
          value={apiKey}
          placeholder={`Paste your ${providerName} API key`}
          disabled={isConnecting}
          onChange={(event) => setApiKey(event.target.value)}
        />
      </label>
      <label>
        <span>Account label <small>Optional</small></span>
        <input
          type="text"
          value={accountLabel}
          placeholder={`${providerName} account`}
          disabled={isConnecting}
          onChange={(event) => setAccountLabel(event.target.value)}
        />
      </label>

      <div className="auth-panel-actions">
        <button className="provider-secondary-button" type="button" disabled={isConnecting} onClick={onBack}>Back</button>
        <button className="provider-primary-button" type="submit" disabled={isConnecting || !apiKey.trim()}>
          {isConnecting ? "Connecting..." : "Connect"}
        </button>
      </div>
    </form>
  );
}
