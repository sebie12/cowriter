from dataclasses import dataclass, field
from typing import Mapping, Protocol


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


@dataclass(frozen=True)
class ChatResult:
    message: str


@dataclass(frozen=True)
class ProviderConfig:
    endpoint_url: str | None = None
    credentials: Mapping[str, str] = field(default_factory=dict, repr=False)


class LLMProvider(Protocol):
    provider_ids: set[str]
    credential_fields: tuple[str, ...]

    def chat(self, request: ChatRequest, config: ProviderConfig) -> ChatResult:
        ...

    def list_models(self, config: ProviderConfig) -> list[str]:
        ...
