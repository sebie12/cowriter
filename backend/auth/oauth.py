import os
import secrets
import threading
import time
from dataclasses import dataclass, field

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

if __package__ and __package__.startswith("backend."):
    from .connections import ProviderConnectionError
else:
    from auth.connections import ProviderConnectionError

GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/cloud-platform",
]
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


@dataclass
class PendingGoogleOAuth:
    flow: Flow = field(repr=False)
    attempt_id: str
    provider_id: str
    project_id: str
    location: str
    account_label: str | None
    created_at: float


@dataclass
class CompletedGoogleOAuth:
    credentials: Credentials = field(repr=False)
    attempt_id: str
    provider_id: str
    project_id: str
    location: str
    account_id: str
    account_label: str


@dataclass
class GoogleOAuthAttempt:
    attempt_id: str
    provider_id: str
    status: str
    error: str | None
    updated_at: float


class GoogleOAuthManager:
    def __init__(self, pending_ttl_seconds: int = 600, attempt_retention_seconds: int = 900):
        self.pending_ttl_seconds = pending_ttl_seconds
        self.attempt_retention_seconds = attempt_retention_seconds
        self._pending: dict[str, PendingGoogleOAuth] = {}
        self._attempts: dict[str, GoogleOAuthAttempt] = {}
        self._lock = threading.Lock()

    def start(
        self,
        *,
        provider_id: str,
        project_id: str,
        location: str,
        account_label: str | None,
        redirect_uri: str,
    ) -> tuple[str, str, str]:
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ProviderConnectionError("Google OAuth is not configured on the backend.", 503)

        if redirect_uri.startswith(("http://127.0.0.1", "http://localhost")):
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=GOOGLE_OAUTH_SCOPES,
            autogenerate_code_verifier=True,
        )
        flow.redirect_uri = redirect_uri
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        attempt_id = secrets.token_urlsafe(24)

        with self._lock:
            self._remove_expired()
            self._pending[state] = PendingGoogleOAuth(
                flow=flow,
                attempt_id=attempt_id,
                provider_id=provider_id,
                project_id=project_id,
                location=location,
                account_label=account_label,
                created_at=time.monotonic(),
            )
            self._attempts[attempt_id] = GoogleOAuthAttempt(
                attempt_id=attempt_id,
                provider_id=provider_id,
                status="connecting",
                error=None,
                updated_at=time.monotonic(),
            )

        return authorization_url, state, attempt_id

    def complete(self, *, state: str, authorization_response: str) -> CompletedGoogleOAuth:
        with self._lock:
            self._remove_expired()
            pending = self._pending.pop(state, None)

        if pending is None:
            raise ProviderConnectionError("Google OAuth request is invalid or expired.", 400)

        try:
            pending.flow.fetch_token(authorization_response=authorization_response)
            credentials = pending.flow.credentials
            account_id, discovered_label = self._load_identity(credentials)
        except ProviderConnectionError:
            self.mark_error(pending.attempt_id, "Google OAuth authorization failed.")
            raise
        except Exception as error:
            self.mark_error(pending.attempt_id, "Google OAuth authorization could not be completed.")
            raise ProviderConnectionError("Google OAuth authorization could not be completed.", 400) from error

        return CompletedGoogleOAuth(
            credentials=credentials,
            attempt_id=pending.attempt_id,
            provider_id=pending.provider_id,
            project_id=pending.project_id,
            location=pending.location,
            account_id=account_id,
            account_label=pending.account_label or discovered_label,
        )

    def get_attempt(self, *, provider_id: str, attempt_id: str) -> GoogleOAuthAttempt:
        with self._lock:
            self._remove_expired()
            attempt = self._attempts.get(attempt_id)
            if attempt is None or attempt.provider_id != provider_id:
                raise ProviderConnectionError("OAuth connection attempt was not found.", 404)

            return GoogleOAuthAttempt(
                attempt_id=attempt.attempt_id,
                provider_id=attempt.provider_id,
                status=attempt.status,
                error=attempt.error,
                updated_at=attempt.updated_at,
            )

    def mark_connected(self, attempt_id: str) -> None:
        self._set_attempt_status(attempt_id, "connected", None)

    def mark_error(self, attempt_id: str, error: str) -> None:
        self._set_attempt_status(attempt_id, "error", error)

    def _set_attempt_status(self, attempt_id: str, status: str, error: str | None) -> None:
        with self._lock:
            attempt = self._attempts.get(attempt_id)
            if attempt is None:
                return

            attempt.status = status
            attempt.error = error
            attempt.updated_at = time.monotonic()

    def _load_identity(self, credentials: Credentials) -> tuple[str, str]:
        response = AuthorizedSession(credentials).get(GOOGLE_USERINFO_URL, timeout=10)
        if not response.ok:
            raise ProviderConnectionError("Google account information could not be loaded.", 502)

        identity = response.json()
        account_id = identity.get("sub") or identity.get("email")
        account_label = identity.get("email") or account_id
        if not isinstance(account_id, str) or not isinstance(account_label, str):
            raise ProviderConnectionError("Google account information was incomplete.", 502)

        return account_id, account_label

    def _remove_expired(self) -> None:
        now = time.monotonic()
        cutoff = now - self.pending_ttl_seconds
        expired_states = [
            state
            for state, pending in self._pending.items()
            if pending.created_at < cutoff
        ]
        for state in expired_states:
            pending = self._pending[state]
            attempt = self._attempts.get(pending.attempt_id)
            if attempt is not None:
                attempt.status = "error"
                attempt.error = "Google OAuth request expired."
                attempt.updated_at = now
            del self._pending[state]

        attempt_cutoff = now - self.attempt_retention_seconds
        expired_attempt_ids = [
            attempt_id
            for attempt_id, attempt in self._attempts.items()
            if attempt.updated_at < attempt_cutoff
        ]
        for attempt_id in expired_attempt_ids:
            del self._attempts[attempt_id]


google_oauth_manager = GoogleOAuthManager()
