from collections.abc import Callable, Iterator
from typing import Any

if __package__ and __package__.startswith("backend."):
    from ..auth.connections import normalize_identifier
    from ..auth.credentials import CredentialStore
else:
    from auth.connections import normalize_identifier
    from auth.credentials import CredentialStore

from .contracts import ChatRequest, ChatResult, LLMError, LLMProvider, ProviderConfig


class ChatService:
    def __init__(
        self,
        connection_lookup: Callable[[int], Any],
        credential_store: CredentialStore | None = None,
        providers: list[LLMProvider] | None = None,
    ):
        self.connection_lookup = connection_lookup
        self.credential_store = credential_store or CredentialStore()
        self.providers = providers if providers is not None else self._default_providers()

    def chat(self, request: ChatRequest) -> ChatResult:
        provider, config = self._resolve_provider(
            connection_id=request.connection_id,
            requested_provider=request.provider,
        )
        return provider.chat(request, config)

    def stream_chat(self, request: ChatRequest) -> Iterator[str]:
        provider, config = self._resolve_provider(
            connection_id=request.connection_id,
            requested_provider=request.provider,
        )
        return provider.stream_chat(request, config)

    def supports_provider(self, provider_id: str) -> bool:
        normalized_provider_id = normalize_identifier(provider_id)
        return any(
            normalized_provider_id in provider.provider_ids
            for provider in self.providers
        )

    def list_models(self, connection_id: int) -> tuple[str, list[str]]:
        connection = self.connection_lookup(connection_id)
        if connection is None:
            raise LLMError("Provider connection not found.", 404)

        provider_id = normalize_identifier(connection.provider)
        provider = self._find_provider(provider_id)
        config = self._configuration(provider, connection)
        return provider_id, provider.list_models(config)

    def _resolve_provider(
        self,
        *,
        connection_id: int,
        requested_provider: str,
    ) -> tuple[LLMProvider, ProviderConfig]:
        provider_id = normalize_identifier(requested_provider)
        provider = self._find_provider(provider_id)
        connection = self.connection_lookup(connection_id)

        if connection is None:
            raise LLMError("Provider connection not found.", 404)
        if normalize_identifier(connection.provider) != provider_id:
            raise LLMError("Provider does not match the selected connection.")

        return provider, self._configuration(provider, connection)

    def _configuration(self, provider: LLMProvider, connection: Any) -> ProviderConfig:
        if connection.status != "connected":
            raise LLMError("Provider is not connected.", 409)

        try:
            credentials = self.credential_store.get_many(
                normalize_identifier(connection.provider),
                connection.account_id,
                provider.credential_fields,
            )
        except Exception as error:
            raise LLMError("Could not load provider credentials.", 500) from error
        missing_fields = [
            field for field in provider.credential_fields if not credentials.get(field)
        ]
        if missing_fields:
            raise LLMError("Provider credentials are not configured.", 409)

        return ProviderConfig(
            endpoint_url=connection.endpoint_url,
            credentials=credentials,
        )

    def _find_provider(self, provider_id: str) -> LLMProvider:
        for provider in self.providers:
            if provider_id in provider.provider_ids:
                return provider

        raise LLMError(f"Unsupported chat provider: {provider_id}.", 400)

    def _default_providers(self) -> list[LLMProvider]:
        if __package__ and __package__.startswith("backend."):
            from ..auth.providers.Ollama import OllamaProvider
            from ..auth.providers.Openai import OpenAIProvider
        else:
            from auth.providers.Ollama import OllamaProvider
            from auth.providers.Openai import OpenAIProvider

        return [OpenAIProvider(), OllamaProvider()]
