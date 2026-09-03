import unittest
from types import SimpleNamespace

from backend.llm import ChatRequest, ChatResult, LLMError, ModelTurn, ToolCall
from backend.services import ChatService


class FakeCredentialStore:
    def __init__(self, credentials=None):
        self.credentials = credentials or {}
        self.call = None

    def get_many(self, provider, account_id, fields):
        self.call = (provider, account_id, fields)
        return {
            field: self.credentials[field]
            for field in fields
            if field in self.credentials
        }


class FakeProvider:
    provider_ids = {"openai"}
    credential_fields = ("api_key",)

    def __init__(self):
        self.chat_call = None
        self.stream_chat_call = None
        self.models_config = None
        self.complete_chat_calls = []
        self.turns = []

    def chat(self, request, config):
        self.chat_call = (request, config)
        return ChatResult(message="answer")

    def stream_chat(self, request, config):
        self.stream_chat_call = (request, config)
        return iter(["streamed ", "answer"])

    def complete_chat(self, request, config, messages, tools):
        self.complete_chat_calls.append((request, config, list(messages), tools))
        return self.turns.pop(0)

    def list_models(self, config):
        self.models_config = config
        return ["gpt-test"]


class FakeOllamaProvider(FakeProvider):
    provider_ids = {"ollama"}
    credential_fields = ()


class FakeMCPClient:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exception_type, _exception, _traceback):
        return False

    async def list_tools(self):
        return [SimpleNamespace(
            name="read_file",
            description="Read a project file.",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
        )]

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return SimpleNamespace(
            structured_content={"content": "project text"},
            content=[],
            is_error=False,
        )


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.connection = SimpleNamespace(
            provider="openai",
            account_id="account-1",
            endpoint_url=None,
            status="connected",
        )
        self.provider = FakeProvider()
        self.credentials = FakeCredentialStore({"api_key": "secret"})
        self.service = ChatService(
            connection_lookup=lambda connection_id: self.connection if connection_id == 7 else None,
            credential_store=self.credentials,
            providers=[self.provider, FakeOllamaProvider()],
        )

    def test_selects_provider_and_passes_normalized_configuration(self):
        request = ChatRequest(7, "OpenAI", "gpt-test", "Hello")

        result = self.service.chat(request)

        self.assertEqual(result.message, "answer")
        self.assertEqual(self.provider.chat_call[0], request)
        self.assertEqual(self.provider.chat_call[1].credentials, {"api_key": "secret"})
        self.assertEqual(self.credentials.call, ("openai", "account-1", ("api_key",)))

    def test_lists_models_through_selected_provider(self):
        provider_id, models = self.service.list_models(7)

        self.assertEqual(provider_id, "openai")
        self.assertEqual(models, ["gpt-test"])
        self.assertEqual(self.provider.models_config.credentials, {"api_key": "secret"})

    def test_streams_chat_through_selected_provider(self):
        request = ChatRequest(7, "OpenAI", "gpt-test", "Hello")

        chunks = list(self.service.stream_chat(request))

        self.assertEqual(chunks, ["streamed ", "answer"])
        self.assertEqual(self.provider.stream_chat_call[0], request)
        self.assertEqual(self.provider.stream_chat_call[1].credentials, {"api_key": "secret"})

    def test_feeds_mcp_tools_and_results_to_provider(self):
        mcp_client = FakeMCPClient()
        self.provider.turns = [
            ModelTurn("", (ToolCall("call-1", "read_file", {"path": "draft.txt"}),)),
            ModelTurn("Answer from the project file."),
        ]
        service = ChatService(
            connection_lookup=lambda _connection_id: self.connection,
            credential_store=self.credentials,
            providers=[self.provider],
            project_lookup=lambda _project_id: SimpleNamespace(path="/tmp/project"),
            mcp_client_factory=lambda _project_path: mcp_client,
        )

        chunks = list(service.stream_chat(
            ChatRequest(7, "openai", "gpt-test", "Read it", project_id=3)
        ))

        self.assertEqual(chunks, ["Answer from the project file."])
        self.assertEqual(mcp_client.calls, [("read_file", {"path": "draft.txt"})])
        self.assertEqual(self.provider.complete_chat_calls[0][3][0].name, "read_file")
        self.assertEqual(self.provider.complete_chat_calls[1][2][-1], {
            "role": "tool",
            "tool_call_id": "call-1",
            "tool_name": "read_file",
            "content": '{"content": "project text"}',
        })

    def test_rejects_connection_provider_mismatch(self):
        request = ChatRequest(7, "ollama", "model", "Hello")

        with self.assertRaisesRegex(LLMError, "does not match"):
            self.service.chat(request)

    def test_reports_supported_providers(self):
        self.assertTrue(self.service.supports_provider("OpenAI"))
        self.assertTrue(self.service.supports_provider("ollama"))
        self.assertFalse(self.service.supports_provider("gemini"))

    def test_rejects_missing_credentials(self):
        self.credentials.credentials = {}

        with self.assertRaisesRegex(LLMError, "credentials are not configured") as raised:
            self.service.chat(ChatRequest(7, "openai", "model", "Hello"))

        self.assertEqual(raised.exception.status_code, 409)

    def test_rejects_missing_connection(self):
        with self.assertRaisesRegex(LLMError, "not found") as raised:
            self.service.chat(ChatRequest(99, "openai", "model", "Hello"))

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
