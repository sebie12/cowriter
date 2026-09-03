import hashlib
import json
from collections.abc import Iterator
from typing import Any

import openai

if __package__ and __package__.startswith("backend."):
    from ..connections import ProviderConnectionError, ProviderConnectionResult, ProviderConnector
    from ...llm import (
        ChatRequest,
        ChatResult,
        LLMError,
        ModelTurn,
        ProviderConfig,
        ToolCall,
        ToolDefinition,
    )
else:
    from auth.connections import ProviderConnectionError, ProviderConnectionResult, ProviderConnector
    from llm import (
        ChatRequest,
        ChatResult,
        LLMError,
        ModelTurn,
        ProviderConfig,
        ToolCall,
        ToolDefinition,
    )


class OpenAIProvider:
    provider_ids = {"openai"}
    credential_fields = ("api_key",)

    def __init__(self, client_factory=openai.OpenAI):
        self.client_factory = client_factory

    def validate_api_key(self, api_key: str) -> None:
        try:
            with self.client_factory(api_key=api_key, timeout=15.0, max_retries=0) as client:
                client.models.list()
        except openai.AuthenticationError as error:
            raise ProviderConnectionError("OpenAI API key could not be validated.") from error
        except openai.APIConnectionError as error:
            raise ProviderConnectionError("Could not connect to OpenAI right now.", 502) from error
        except openai.APIError as error:
            raise ProviderConnectionError("OpenAI API key could not be validated.") from error

    def create_connection(
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
        self.validate_api_key(api_key)
        fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]
        account_label = payload.get("account_label")
        if not isinstance(account_label, str) or not account_label.strip():
            account_label = f"{provider_name} API key"

        return ProviderConnectionResult(
            provider_id=provider_id,
            auth_method=auth_method,
            account_id=f"{provider_id}-api-key-{fingerprint}",
            account_label=account_label.strip(),
            credentials={"api_key": api_key},
        )

    def list_models(self, config: ProviderConfig) -> list[str]:
        api_key = self._api_key(config)
        try:
            with self.client_factory(api_key=api_key, timeout=30.0, max_retries=0) as client:
                response = client.models.list()
        except openai.AuthenticationError as error:
            raise LLMError("OpenAI credentials are invalid.", 401) from error
        except openai.APIConnectionError as error:
            raise LLMError("Could not connect to OpenAI right now.", 502) from error
        except openai.APIError as error:
            raise LLMError("Could not retrieve models from OpenAI.", 502) from error

        return sorted(
            {
                model.id.strip()
                for model in response.data
                if isinstance(model.id, str) and model.id.strip()
            },
            key=str.casefold,
        )

    def chat(self, request: ChatRequest, config: ProviderConfig) -> ChatResult:
        return ChatResult(message="".join(self.stream_chat(request, config)))

    def stream_chat(
        self,
        request: ChatRequest,
        config: ProviderConfig,
    ) -> Iterator[str]:
        api_key = self._api_key(config)
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(request.model_messages())

        try:
            with self.client_factory(api_key=api_key, timeout=120.0, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=request.model,
                    messages=messages,
                    stream=True,
                )
                has_content = False
                for chunk in response:
                    content = chunk.choices[0].delta.content if chunk.choices else None
                    if isinstance(content, str) and content:
                        if content.strip():
                            has_content = True
                        yield content
        except openai.AuthenticationError as error:
            raise LLMError("OpenAI credentials are invalid.", 401) from error
        except openai.NotFoundError as error:
            raise LLMError("The selected OpenAI model was not found.", 404) from error
        except openai.BadRequestError as error:
            raise LLMError("OpenAI rejected the selected model or chat request.", 400) from error
        except openai.RateLimitError as error:
            raise LLMError("OpenAI rate limit exceeded. Try again later.", 429) from error
        except openai.APIConnectionError as error:
            raise LLMError("Could not connect to OpenAI right now.", 502) from error
        except openai.APIError as error:
            raise LLMError("OpenAI could not complete the chat request.", 502) from error

        if not has_content:
            raise LLMError("OpenAI returned an empty response.", 502)

    def complete_chat(
        self,
        request: ChatRequest,
        config: ProviderConfig,
        messages: list[dict[str, Any]],
        tools: tuple[ToolDefinition, ...],
    ) -> ModelTurn:
        api_key = self._api_key(config)
        openai_messages = []
        for message in messages:
            converted = dict(message)
            converted.pop("tool_name", None)
            openai_messages.append(converted)
        try:
            with self.client_factory(api_key=api_key, timeout=120.0, max_retries=0) as client:
                response = client.chat.completions.create(
                    model=request.model,
                    messages=openai_messages,
                    tools=[tool.model_payload() for tool in tools],
                    stream=False,
                )
        except openai.AuthenticationError as error:
            raise LLMError("OpenAI credentials are invalid.", 401) from error
        except openai.NotFoundError as error:
            raise LLMError("The selected OpenAI model was not found.", 404) from error
        except openai.BadRequestError as error:
            raise LLMError("OpenAI rejected the selected model or chat request.", 400) from error
        except openai.RateLimitError as error:
            raise LLMError("OpenAI rate limit exceeded. Try again later.", 429) from error
        except openai.APIConnectionError as error:
            raise LLMError("Could not connect to OpenAI right now.", 502) from error
        except openai.APIError as error:
            raise LLMError("OpenAI could not complete the chat request.", 502) from error

        if not response.choices:
            raise LLMError("OpenAI returned an empty response.", 502)

        message = response.choices[0].message
        tool_calls = []
        for call in message.tool_calls or ():
            try:
                arguments = json.loads(call.function.arguments)
            except (TypeError, json.JSONDecodeError) as error:
                raise LLMError("OpenAI returned invalid tool arguments.", 502) from error
            if not isinstance(arguments, dict):
                raise LLMError("OpenAI returned invalid tool arguments.", 502)
            tool_calls.append(ToolCall(call.id, call.function.name, arguments))

        content = message.content or ""
        if not content.strip() and not tool_calls:
            raise LLMError("OpenAI returned an empty response.", 502)
        return ModelTurn(content=content, tool_calls=tuple(tool_calls))

    def _api_key(self, config: ProviderConfig) -> str:
        api_key = config.credentials.get("api_key")
        if not isinstance(api_key, str) or not api_key.strip():
            raise LLMError("OpenAI API key is not configured.", 409)
        return api_key.strip()


class OpenAIConnector(ProviderConnector):
    provider_ids = {"openai"}
    auth_methods = {"api_key"}

    def __init__(self, provider: OpenAIProvider | None = None):
        self.provider = provider or OpenAIProvider()

    def connect(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method: str,
        payload: dict[str, Any],
    ) -> ProviderConnectionResult:
        return self.provider.create_connection(
            provider_id=provider_id,
            provider_name=provider_name,
            auth_method=auth_method,
            payload=payload,
        )
