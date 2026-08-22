import hashlib
from typing import Any

from google import genai
from google.genai import errors
from google.oauth2.credentials import Credentials

if __package__ and __package__.startswith("backend."):
    from ..connections import ProviderAuthorizationResult, ProviderConnectionError, ProviderConnectionResult, ProviderConnector
    from ..oauth import GoogleOAuthManager, google_oauth_manager
else:
    from auth.connections import ProviderAuthorizationResult, ProviderConnectionError, ProviderConnectionResult, ProviderConnector
    from auth.oauth import GoogleOAuthManager, google_oauth_manager


class GeminiProvider:
    def __init__(self, oauth_manager: GoogleOAuthManager | None = None):
        self.client = None
        self.models = None
        self.oauth_manager = oauth_manager or google_oauth_manager

    def api_key_connection(self, api_key: str) -> tuple[bool, list[Any]]:
        self.client = genai.Client(api_key=api_key)
        models = self._load_models("Google API key could not be validated.")
        return True, models

    def oauth_connection(
        self,
        *,
        provider_id: str,
        project_id: str,
        location: str,
        account_label: str | None,
        redirect_uri: str,
    ) -> ProviderAuthorizationResult:
        if not project_id.strip():
            raise ProviderConnectionError("project_id is required for Google OAuth.")

        authorization_url, _state, attempt_id = self.oauth_manager.start(
            provider_id=provider_id,
            project_id=project_id.strip(),
            location=location.strip() or "us-central1",
            account_label=account_label.strip() if account_label else None,
            redirect_uri=redirect_uri,
        )
        return ProviderAuthorizationResult(
            provider_id=provider_id,
            auth_method="oauth",
            attempt_id=attempt_id,
            authorization_url=authorization_url,
        )

    def _validate_oauth_credentials(
        self,
        credentials: Credentials,
        project_id: str,
        location: str,
    ) -> tuple[bool, list[Any]]:
        self.client = genai.Client(
            vertexai=True,
            project=project_id.strip(),
            location=location.strip() or "us-central1",
            credentials=credentials,
        )
        models = self._load_models("Google OAuth credentials could not be validated.")
        return True, models

    def _load_models(self, invalid_credentials_message: str) -> list[Any]:
        if self.client is None:
            raise ProviderConnectionError("Gemini client is not initialized.", 500)

        try:
            models = list(self.client.models.list())
        except errors.ClientError as error:
            self.client = None
            self.models = None
            raise ProviderConnectionError(invalid_credentials_message, 400) from error
        except errors.APIError as error:
            self.client = None
            self.models = None
            raise ProviderConnectionError("Could not connect to Google Gemini right now.", 502) from error

        self.models = models
        return models

    def create_api_key_connection(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method: str,
        payload: dict[str, Any],
    ) -> ProviderConnectionResult:
        api_key = payload.get("api_key")
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderConnectionError("api_key is required.")

        api_key = api_key.strip()
        self.api_key_connection(api_key)

        account_id = self._account_id(provider_id, api_key)
        account_label = payload.get("account_label")
        if not isinstance(account_label, str) or not account_label.strip():
            account_label = f"{provider_name} API key"

        return ProviderConnectionResult(
            provider_id=provider_id,
            auth_method=auth_method,
            account_id=account_id,
            account_label=account_label.strip(),
            credentials={"api_key": api_key},
        )
    

    def create_oauth_connection(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method: str,
        credentials: Credentials,
        project_id: str,
        location: str,
        account_id: str,
        account_label: str | None,
    ) -> ProviderConnectionResult:
        self._validate_oauth_credentials(credentials, project_id, location)

        normalized_account_id = account_id.strip()
        if not normalized_account_id:
            raise ProviderConnectionError("account_id is required for Google OAuth.")

        normalized_account_label = account_label.strip() if account_label else ""
        if not normalized_account_label:
            normalized_account_label = f"{provider_name} ({normalized_account_id})"

        return ProviderConnectionResult(
            provider_id=provider_id,
            auth_method=auth_method,
            account_id=normalized_account_id,
            account_label=normalized_account_label,
            credentials={
                "oauth_credentials": credentials.to_json(),
                "project_id": project_id.strip(),
                "location": location.strip() or "us-central1",
            },
        )

    def get_models(self):
        if self.client is None or self.models is None:
            raise ValueError("Client is not initialized. Please connect first.")

        return self.models

    def _account_id(self, provider_id: str, api_key: str) -> str:
        fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
        return f"{provider_id}-api-key-{fingerprint}"


class GeminiConnector(ProviderConnector):
    provider_ids = {"gemini", "google", "google_gemini"}
    auth_methods = {"api_key", "oauth"}

    def __init__(self, provider: GeminiProvider | None = None):
        self.provider = provider or GeminiProvider()

    def connect(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method: str,
        payload: dict[str, Any],
    ) -> ProviderConnectionResult | ProviderAuthorizationResult:
        if auth_method == "api_key":
            return self.provider.create_api_key_connection(
                provider_id=provider_id,
                provider_name=provider_name,
                auth_method=auth_method,
                payload=payload,
            )

        project_id = payload.get("project_id")
        location = payload.get("location", "us-central1")
        account_label = payload.get("account_label")

        if not isinstance(project_id, str) or not project_id.strip():
            raise ProviderConnectionError("project_id is required for Google OAuth.")
        if not isinstance(location, str):
            raise ProviderConnectionError("location must be a string.")
        if account_label is not None and not isinstance(account_label, str):
            raise ProviderConnectionError("account_label must be a string.")

        credentials = payload.get("credentials")
        if not isinstance(credentials, Credentials):
            redirect_uri = payload.get("redirect_uri")
            if not isinstance(redirect_uri, str) or not redirect_uri.strip():
                raise ProviderConnectionError("redirect_uri is required for Google OAuth.", 500)

            return self.provider.oauth_connection(
                provider_id=provider_id,
                project_id=project_id,
                location=location,
                account_label=account_label,
                redirect_uri=redirect_uri,
            )

        account_id = payload.get("account_id") or getattr(credentials, "account", None)
        if not isinstance(account_id, str) or not account_id.strip():
            raise ProviderConnectionError("account_id is required for Google OAuth.")

        return self.provider.create_oauth_connection(
            provider_id=provider_id,
            provider_name=provider_name,
            auth_method=auth_method,
            credentials=credentials,
            project_id=project_id,
            location=location,
            account_id=account_id,
            account_label=account_label,
        )
