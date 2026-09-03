import asyncio
import json
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

if __package__ and __package__.startswith("backend."):
    from ..auth.connections import normalize_identifier
    from ..auth.credentials import CredentialStore
    from ..llm.contracts import (
        ChatRequest,
        ChatResult,
        LLMError,
        LLMProvider,
        ModelTurn,
        ProviderConfig,
        ToolCall,
        ToolDefinition,
    )
    from ..mcp_client import MCPClient
else:
    from auth.connections import normalize_identifier
    from auth.credentials import CredentialStore
    from llm.contracts import (
        ChatRequest,
        ChatResult,
        LLMError,
        LLMProvider,
        ModelTurn,
        ProviderConfig,
        ToolCall,
        ToolDefinition,
    )
    from mcp_client import MCPClient


MAX_TOOL_ROUNDS = 5


class ChatService:
    def __init__(
        self,
        connection_lookup: Callable[[int], Any],
        credential_store: CredentialStore | None = None,
        providers: list[LLMProvider] | None = None,
        project_lookup: Callable[[int], Any] | None = None,
        mcp_client_factory: Callable[[str], MCPClient] | None = None,
    ):
        self.connection_lookup = connection_lookup
        self.credential_store = credential_store or CredentialStore()
        self.providers = providers if providers is not None else self._default_providers()
        self.project_lookup = project_lookup
        self.mcp_client_factory = mcp_client_factory or self._default_mcp_client

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
        project_path = self._project_path(request.project_id)
        if project_path is None:
            return provider.stream_chat(request, config)

        try:
            message = asyncio.run(
                self._chat_with_tools(request, provider, config, project_path)
            )
        except LLMError:
            raise
        except Exception as error:
            raise LLMError("Could not communicate with the project tools.", 502) from error
        return iter([message])

    async def _chat_with_tools(
        self,
        request: ChatRequest,
        provider: LLMProvider,
        config: ProviderConfig,
        project_path: str,
    ) -> str:
        async with self.mcp_client_factory(project_path) as client:
            mcp_tools = await client.list_tools()
            tools = tuple(
                ToolDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.input_schema,
                )
                for tool in mcp_tools
            )
            if not tools:
                return "".join(provider.stream_chat(request, config))

            messages: list[dict[str, Any]] = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.model_messages())

            for _ in range(MAX_TOOL_ROUNDS):
                turn = provider.complete_chat(request, config, messages, tools)
                if not turn.tool_calls:
                    return turn.content

                messages.append(self._assistant_tool_message(turn))
                for call in turn.tool_calls:
                    result = await client.call_tool(call.name, call.arguments)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "tool_name": call.name,
                        "content": self._serialize_mcp_result(result),
                    })

        raise LLMError("Maximum tool-call rounds exceeded.", 502)

    @staticmethod
    def _assistant_tool_message(turn: ModelTurn) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": turn.content or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in turn.tool_calls
            ],
        }

    @staticmethod
    def _serialize_mcp_result(result: Any) -> str:
        structured_content = getattr(result, "structured_content", None)
        if structured_content is not None:
            content = json.dumps(structured_content, ensure_ascii=True)
        else:
            parts = []
            for item in getattr(result, "content", ()):
                text = getattr(item, "text", None)
                parts.append(
                    text
                    if isinstance(text, str)
                    else json.dumps(item.model_dump(mode="json", by_alias=True), ensure_ascii=True)
                )
            content = "\n".join(parts)
        if getattr(result, "is_error", False):
            return f"Tool error: {content}"
        return content

    def _project_path(self, project_id: int | None) -> str | None:
        if project_id is None or self.project_lookup is None:
            return None
        project = self.project_lookup(project_id)
        if project is None:
            raise LLMError("Project not found.", 404)
        path = getattr(project, "path", None)
        return path.strip() if isinstance(path, str) and path.strip() else None

    @staticmethod
    def _default_mcp_client(project_path: str) -> MCPClient:
        workspace_root = Path(__file__).resolve().parents[2]
        return MCPClient(
            sys.executable,
            ["-m", "backend.mcp_server"],
            env={"COWRITER_PROJECT_PATH": project_path},
            cwd=workspace_root,
        )

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
