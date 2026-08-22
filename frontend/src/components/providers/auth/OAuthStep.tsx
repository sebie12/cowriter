interface OAuthStepProps {
  providerName: string;
  isConnecting: boolean;
  isWaiting: boolean;
  canReopenBrowser: boolean;
  onBack: () => void;
  onCancel: () => void;
  onReopenBrowser: () => void;
  onSignIn: () => Promise<boolean>;
}

function oauthProviderName(providerName: string): string {
  return /google|gemini/i.test(providerName) ? "Google" : providerName;
}

export function OAuthStep({
  providerName,
  isConnecting,
  isWaiting,
  canReopenBrowser,
  onBack,
  onCancel,
  onReopenBrowser,
  onSignIn,
}: OAuthStepProps) {
  const signInProviderName = oauthProviderName(providerName);

  if (isWaiting) {
    return (
      <div className="auth-step oauth-browser-step">
        <div className="oauth-browser-visual oauth-browser-visual-waiting" aria-hidden="true">
          <span className="oauth-spinner" />
        </div>
        <div className="auth-step-heading oauth-browser-copy">
          <span>Browser authentication</span>
          <h3>Waiting for sign-in</h3>
          <p>Complete the sign-in process in your browser. This window will update automatically when authentication is complete.</p>
        </div>
        <div className="oauth-waiting-message" role="status">
          <strong>You haven't completed authentication yet.</strong>
          <span>Open your browser and sign in to continue.</span>
        </div>
        <div className="auth-panel-actions oauth-browser-actions">
          {canReopenBrowser && (
            <button className="provider-secondary-button" type="button" onClick={onReopenBrowser}>
              Open browser again
            </button>
          )}
          <button className="provider-secondary-button" type="button" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-step oauth-browser-step">
      <div className="oauth-browser-visual" aria-hidden="true">
        <span className="oauth-browser-ring" />
      </div>
      <div className="auth-step-heading oauth-browser-copy">
        <span>Step 2 of 2</span>
        <h3>Sign in using your browser</h3>
        <p>You'll be redirected to your browser to sign in with {signInProviderName} and authorize Cowriter.</p>
      </div>
      <p className="oauth-security-note">Your password and OAuth credentials are handled by {signInProviderName} and the Cowriter backend. You never enter them in Cowriter.</p>
      <div className="auth-panel-actions oauth-browser-actions">
        <button className="provider-secondary-button" type="button" disabled={isConnecting} onClick={onBack}>Back</button>
        <button
          className="provider-primary-button"
          type="button"
          disabled={isConnecting}
          onClick={() => void onSignIn()}
        >
          {isConnecting ? "Opening browser..." : `Sign in with ${signInProviderName}`}
        </button>
      </div>
    </div>
  );
}
