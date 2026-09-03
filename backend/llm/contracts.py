from dataclasses import dataclass, field
from collections.abc import Iterator
from typing import Any, Mapping, Protocol


def format_chat_message(role: str, content: str) -> str:
    return f"<|im_start|>{role}\n{content}<|im_end|>"


class LLMError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ChatRequest:
    connection_id: int
    provider: str
    model: str
    message: str
    system_prompt: str | None = None
    history: tuple[dict[str, str], ...] = ()
    project_id: int | None = None

    def model_messages(self) -> list[dict[str, str]]:
        messages = [
            {
                "role": history_message["role"],
                "content": format_chat_message(
                    history_message["role"],
                    history_message["content"],
                ),
            }
            for history_message in self.history
        ]
        messages.append({
            "role": "user",
            "content": format_chat_message("user", self.message),
        })
        return messages


@dataclass(frozen=True)
class ChatResult:
    message: str


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]

    def model_payload(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class ProviderConfig:
    endpoint_url: str | None = None
    credentials: Mapping[str, str] = field(default_factory=dict, repr=False)


class LLMProvider(Protocol):
    provider_ids: set[str]
    credential_fields: tuple[str, ...]

    def chat(self, request: ChatRequest, config: ProviderConfig) -> ChatResult:
        ...

    def stream_chat(self, request: ChatRequest, config: ProviderConfig) -> Iterator[str]:
        ...

    def complete_chat(
        self,
        request: ChatRequest,
        config: ProviderConfig,
        messages: list[dict[str, Any]],
        tools: tuple[ToolDefinition, ...],
    ) -> ModelTurn:
        ...

    def list_models(self, config: ProviderConfig) -> list[str]:
        ...
