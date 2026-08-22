from dataclasses import dataclass, field
from typing import Any


def normalize_identifier(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def normalize_auth_method(value: str) -> str:
    normalized = normalize_identifier(value).replace(".", "_")
    if normalized in {"oauth", "oauth2", "oauth_2", "oauth_2_0"}:
        return "oauth"
    if normalized in {"api_key", "apikey"}:
        return "api_key"

    return normalized


class ProviderConnectionError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass
class ProviderConnectionResult:
    provider_id: str
    auth_method: str
    account_id: str
    account_label: str
    credentials: dict[str, str] = field(repr=False)
    status: str = "connected"
    endpoint_url: str | None = None


@dataclass
class ProviderAuthorizationResult:
    provider_id: str
    auth_method: str
    attempt_id: str
    authorization_url: str = field(repr=False)
    status: str = "connecting"


class ProviderConnector:
    provider_ids: set[str] = set()
    auth_methods: set[str] = set()

    def supports(self, provider_id: str, auth_method: str) -> bool:
        return provider_id in self.provider_ids and auth_method in self.auth_methods

    def connect(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method: str,
        payload: dict[str, Any],
    ) -> ProviderConnectionResult | ProviderAuthorizationResult:
        raise NotImplementedError


class ProviderConnectionManager:
    def __init__(self, connectors: list[ProviderConnector] | None = None):
        if connectors is None:
            self.connectors = self._default_connectors()
        else:
            self.connectors = connectors

    def connect(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method_name: str,
        payload: dict[str, Any],
    ) -> ProviderConnectionResult | ProviderAuthorizationResult:
        normalized_auth_method = normalize_auth_method(auth_method_name)
        connector = self._find_connector(provider_id, normalized_auth_method)

        return connector.connect(
            provider_id=provider_id,
            provider_name=provider_name,
            auth_method=normalized_auth_method,
            payload=payload,
        )

    def _find_connector(self, provider_id: str, auth_method_name: str) -> ProviderConnector:
        for connector in self.connectors:
            if connector.supports(provider_id, auth_method_name):
                return connector

        raise ProviderConnectionError("Connection flow is not implemented for this provider auth method.", 501)

    def _default_connectors(self) -> list[ProviderConnector]:
        if __package__ and __package__.startswith("backend."):
            from .providers.Gemini import GeminiConnector
            from .providers.Ollama import OllamaConnector
        else:
            from auth.providers.Gemini import GeminiConnector
            from auth.providers.Ollama import OllamaConnector

        return [GeminiConnector(), OllamaConnector()]
