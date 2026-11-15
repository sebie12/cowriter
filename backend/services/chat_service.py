import asyncio
import json
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.auth.connections import normalize_identifier
from backend.auth.credentials import CredentialStore
from backend.llm.contracts import (
    ChatRequest,
    ChatResult,
    LLMError,
    LLMProvider,
    ModelTurn,
    ProviderConfig,
    ToolCall,
    ToolDefinition,
)
from backend.mcp_client import MCPClient


MAX_TOOL_ROUNDS = 5


class ChatService:
    def __init__(
        self,
        connection_lookup: Callable[[int], Any],
        credential_store: CredentialStore | None = None,
        providers: list[LLMProvider] | None = None,
        project_lookup: Callable[[int], Any] | None = None,
        mcp_client_factory: Callable[[str], MCPClient] | None = None,
        conversation_resolver: Callable[[int], Any] | None = None,
        tool_call_service: Any | None = None,
    ):
        self.connection_lookup = connection_lookup
        self.credential_store = credential_store or CredentialStore()
        self.providers = providers if providers is not None else self._default_providers()
        self.project_lookup = project_lookup
        self.mcp_client_factory = mcp_client_factory or self._default_mcp_client
        self.conversation_resolver = conversation_resolver
        self.tool_call_service = tool_call_service

    def chat(self, request: ChatRequest) -> ChatResult:
        provider, config = self.resolve_provider(
            connection_id=request.connection_id,
            requested_provider=request.provider,
        )
        return provider.chat(request, config)

    def stream_chat(self, request: ChatRequest) -> Iterator[dict[str, Any]]:
        provider, config = self.resolve_provider(
            connection_id=request.connection_id,
            requested_provider=request.provider,
        )
        project_path = self._project_path(request.project_id)
        if project_path is None:
            return self._stream_provider(request, provider, config)

        return self._iterate_async_events(
            self._chat_with_tools(request, provider, config, project_path)
        )

    def _stream_provider(
        self,
        request: ChatRequest,
        provider: LLMProvider,
        config: ProviderConfig,
    ) -> Iterator[dict[str, Any]]:
        chunks = iter(provider.stream_chat(request, config))
        try:
            first_chunk = next(chunks)
        except StopIteration:
            return

        message_id = f"assistant-{uuid4()}"
        yield {
            "type": "assistant_start",
            "id": message_id,
            "created_at": self._timestamp(),
        }
        yield {"type": "assistant_delta", "id": message_id, "content": first_chunk}
        for chunk in chunks:
            yield {"type": "assistant_delta", "id": message_id, "content": chunk}
        yield {
            "type": "assistant_end",
            "id": message_id,
            "finished_at": self._timestamp(),
        }

    async def _chat_with_tools(
        self,
        request: ChatRequest,
        provider: LLMProvider,
        config: ProviderConfig,
        project_path: str,
    ) -> AsyncIterator[dict[str, Any]]:
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
                for event in self._stream_provider(request, provider, config):
                    yield event
                return

            messages: list[dict[str, Any]] = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            messages.extend(request.model_messages())
            conversation_id = None

            for _ in range(MAX_TOOL_ROUNDS):
                turn = provider.complete_chat(request, config, messages, tools)
                if turn.content:
                    message_id = f"assistant-{uuid4()}"
                    yield {
                        "type": "assistant_start",
                        "id": message_id,
                        "created_at": self._timestamp(),
                    }
                    yield {
                        "type": "assistant_delta",
                        "id": message_id,
                        "content": turn.content,
                    }
                    yield {
                        "type": "assistant_end",
                        "id": message_id,
                        "finished_at": self._timestamp(),
                    }
                if not turn.tool_calls:
                    return

                messages.append(self._assistant_tool_message(turn))
                for call in turn.tool_calls:
                    record = None
                    if self.tool_call_service is not None:
                        if conversation_id is None:
                            conversation_id = self._resolve_conversation_id(
                                request.project_id
                            )
                        record = self.tool_call_service.start_tool_call(
                            conversation_id=conversation_id,
                            provider_call_id=call.id,
                            tool_name=call.name,
                            input_data=call.arguments,
                        )

                    if record is None:
                        raise LLMError("Could not record the tool call.", 500)
                    yield self._tool_call_event(record)

                    record = self.tool_call_service.mark_tool_call_running(record.id)
                    if record is None:
                        raise LLMError("Could not update the tool call.", 500)
                    yield self._tool_call_event(record)

                    try:
                        result = await client.call_tool(call.name, call.arguments)
                    except Exception as error:
                        if record is not None:
                            failed_record = self.tool_call_service.fail_tool_call(record.id, error)
                            if failed_record is not None:
                                yield self._tool_call_event(failed_record)
                        raise

                    if record is not None:
                        is_error = bool(getattr(result, "is_error", False))
                        completed_record = self.tool_call_service.complete_tool_call(
                            record.id,
                            output_data=self._mcp_result_data(result),
                            is_error=is_error,
                            error=self._serialize_mcp_result(result) if is_error else None,
                        )
                        if completed_record is None:
                            raise LLMError("Could not update the tool call.", 500)
                        yield self._tool_call_event(completed_record)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "tool_name": call.name,
                        "content": self._serialize_mcp_result(result),
                    })

        raise LLMError("Maximum tool-call rounds exceeded.", 502)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _tool_call_event(record: Any) -> dict[str, Any]:
        to_dict = getattr(record, "to_dict", None)
        if not callable(to_dict):
            raise LLMError("Could not serialize the tool call.", 500)
        data = to_dict()
        for timestamp_field in ("created_at", "completed_at"):
            timestamp = data.get(timestamp_field)
            if isinstance(timestamp, str) and not timestamp.endswith(("Z", "+00:00")):
                data[timestamp_field] = f"{timestamp}Z"
        return {"type": "tool_call", "tool_call": data}

    @staticmethod
    def _iterate_async_events(
        events: AsyncIterator[dict[str, Any]],
    ) -> Iterator[dict[str, Any]]:
        loop = asyncio.new_event_loop()
        event_queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
        consumer = loop.create_task(
            ChatService._consume_async_events(events, event_queue)
        )
        try:
            while True:
                event_type, value = loop.run_until_complete(event_queue.get())
                if event_type == "event":
                    yield value
                    continue
                if event_type == "error":
                    if isinstance(value, LLMError):
                        raise value
                    raise LLMError(
                        "Could not communicate with the project tools.", 502
                    ) from value
                if event_type == "done":
                    return
        finally:
            if not consumer.done():
                consumer.cancel()
                try:
                    loop.run_until_complete(consumer)
                except BaseException:
                    pass
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

    @staticmethod
    async def _consume_async_events(
        events: AsyncIterator[dict[str, Any]],
        event_queue: asyncio.Queue[tuple[str, Any]],
    ) -> None:
        try:
            async for event in events:
                await event_queue.put(("event", event))
        except BaseException as error:
            await event_queue.put(("error", error))
        finally:
            await event_queue.put(("done", None))

    def _resolve_conversation_id(self, project_id: int | None) -> int:
        if project_id is None or self.conversation_resolver is None:
            raise LLMError("Tool-call persistence is not configured.", 500)
        conversation = self.conversation_resolver(project_id)
        conversation_id = getattr(conversation, "id", conversation)
        if (
            isinstance(conversation_id, bool)
            or not isinstance(conversation_id, int)
            or conversation_id < 1
        ):
            raise LLMError("Could not resolve the project conversation.", 500)
        return conversation_id

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

    @staticmethod
    def _mcp_result_data(result: Any) -> Any:
        structured_content = getattr(result, "structured_content", None)
        if structured_content is not None:
            return structured_content

        content = []
        for item in getattr(result, "content", ()):
            model_dump = getattr(item, "model_dump", None)
            if callable(model_dump):
                content.append(model_dump(mode="json", by_alias=True))
                continue
            text = getattr(item, "text", None)
            content.append(text if isinstance(text, str) else str(item))
        return {"content": content}

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

    def resolve_provider(
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
        from backend.auth.providers.Ollama import OllamaProvider
        from backend.auth.providers.Openai import OpenAIProvider

        return [OpenAIProvider(), OllamaProvider()]
