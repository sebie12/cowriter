import ipaddress
import os
from typing import Any
from urllib.parse import urlsplit

import ollama

if __package__ and __package__.startswith("backend."):
    from ..connections import ProviderConnectionError, ProviderConnectionResult, ProviderConnector
    from ...llm import ChatRequest, ChatResult, LLMError, ProviderConfig
else:
    from auth.connections import ProviderConnectionError, ProviderConnectionResult, ProviderConnector
    from llm import ChatRequest, ChatResult, LLMError, ProviderConfig

DEFAULT_OLLAMA_SERVER_URL = "http://127.0.0.1:11434"


def normalize_ollama_server_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProviderConnectionError("server_url is required for Ollama.")

    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as error:
        raise ProviderConnectionError("server_url is not a valid URL.") from error

    if parsed.scheme not in {"http", "https"}:
        raise ProviderConnectionError("Ollama server URL must use HTTP or HTTPS.")
    if parsed.username or parsed.password:
        raise ProviderConnectionError("Ollama server URL must not include credentials.")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ProviderConnectionError("Ollama server URL must not include a path, query, or fragment.")

    hostname = parsed.hostname
    if not hostname:
        raise ProviderConnectionError("Ollama server URL must include a host.")

    if hostname.lower() == "localhost":
        hostname = "127.0.0.1"
    else:
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError as error:
            raise ProviderConnectionError("Ollama server must run on this computer.") from error
        if not address.is_loopback:
            raise ProviderConnectionError("Ollama server must run on this computer.")

    formatted_host = f"[{hostname}]" if ":" in hostname else hostname
    port_suffix = f":{port}" if port is not None else ""
    return f"{parsed.scheme}://{formatted_host}{port_suffix}"


class OllamaProvider:
    provider_ids = {"ollama"}
    credential_fields = ()

    def __init__(self, client_factory=ollama.Client):
        self.client_factory = client_factory

    def validate_connection(self, server_url: str) -> str:
        normalized_url = normalize_ollama_server_url(server_url)

        try:
            with self.client_factory(
                host=normalized_url,
                timeout=5.0,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                client.list()
        except ollama.ResponseError as error:
            raise ProviderConnectionError("The configured Ollama server returned an unexpected response.", 502) from error
        except ConnectionError as error:
            raise ProviderConnectionError("Could not connect to Ollama at the configured server URL.", 502) from error
        except Exception as error:
            raise ProviderConnectionError("Could not connect to Ollama at the configured server URL.", 502) from error

        return normalized_url

    def create_connection(
        self,
        *,
        provider_id: str,
        provider_name: str,
        auth_method: str,
        payload: dict[str, Any],
    ) -> ProviderConnectionResult:
        server_url = payload.get("server_url", os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_SERVER_URL))
        if isinstance(server_url, str) and "://" not in server_url:
            server_url = f"http://{server_url}"
        normalized_url = self.validate_connection(server_url)

        account_label = payload.get("account_label")
        if account_label is not None and not isinstance(account_label, str):
            raise ProviderConnectionError("account_label must be a string.")
        if not account_label or not account_label.strip():
            account_label = f"{provider_name} at {urlsplit(normalized_url).netloc}"

        return ProviderConnectionResult(
            provider_id=provider_id,
            auth_method=auth_method,
            account_id=f"{provider_id}-local",
            account_label=account_label.strip(),
            credentials={},
            endpoint_url=normalized_url,
        )

    def list_models(self, config: ProviderConfig) -> list[str]:
        if not config.endpoint_url:
            raise LLMError("Ollama server is not configured.", 409)

        return self._list_models(config.endpoint_url)

    def _list_models(self, endpoint_url: str) -> list[str]:
        try:
            normalized_url = normalize_ollama_server_url(endpoint_url)
        except ProviderConnectionError as error:
            raise LLMError(error.message, error.status_code) from error

        try:
            with self.client_factory(
                host=normalized_url,
                timeout=5.0,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response: ollama.ListResponse = client.list()
        except ollama.ResponseError as error:
            raise LLMError("The configured Ollama server could not list its models.", 502) from error
        except ConnectionError as error:
            raise LLMError("Could not connect to Ollama at the configured server URL.", 502) from error
        except Exception as error:
            raise LLMError("Could not retrieve models from Ollama.", 502) from error

        return sorted(
            {
                item.model.strip()
                for item in response.models
                if isinstance(item.model, str) and item.model.strip()
            },
            key=str.casefold,
        )

    def chat(
        self,
        request: ChatRequest,
        config: ProviderConfig,
    ) -> ChatResult:
        if not config.endpoint_url:
            raise LLMError("Ollama server is not configured.", 409)

        try:
            normalized_url = normalize_ollama_server_url(config.endpoint_url)
        except ProviderConnectionError as error:
            raise LLMError(error.message, error.status_code) from error

        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(request.history)
        messages.append({"role": "user", "content": request.message})

        try:
            with self.client_factory(
                host=normalized_url,
                timeout=120.0,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response: ollama.ChatResponse = client.chat(
                    model=request.model,
                    messages=messages,
                    stream=False,
                )
        except ollama.ResponseError as error:
            if error.status_code == 404:
                raise LLMError("The selected Ollama model is not installed.", 404) from error
            raise LLMError("Ollama could not complete the chat request.", 502) from error
        except ConnectionError as error:
            raise LLMError("Could not connect to Ollama at the configured server URL.", 502) from error
        except Exception as error:
            raise LLMError("Could not communicate with Ollama.", 502) from error

        content = response.message.content
        if not isinstance(content, str) or not content.strip():
            raise LLMError("Ollama returned an empty response.", 502)
        return ChatResult(message=content)


class OllamaConnector(ProviderConnector):
    provider_ids = {"ollama"}
    auth_methods = {"local"}

    def __init__(self, provider: OllamaProvider | None = None):
        self.provider = provider or OllamaProvider()

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
