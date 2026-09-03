import unittest
from types import SimpleNamespace

from backend.auth.providers.Openai import OpenAIProvider
from backend.llm import ChatRequest, LLMError, ProviderConfig, ToolDefinition


class FakeCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, **options):
        self.client.chat_call = options
        if not options.get("stream"):
            return self.client.completion_response
        return self.client.chat_response


class FakeModels:
    def __init__(self, client):
        self.client = client

    def list(self):
        self.client.models_called = True
        return self.client.models_response


class FakeOpenAIClient:
    def __init__(self, chat_content="Test response", chat_chunks=None, completion_response=None, **options):
        self.options = options
        self.chat_call = None
        self.models_called = False
        self.models_response = SimpleNamespace(data=[
            SimpleNamespace(id="gpt-z"),
            SimpleNamespace(id="gpt-a"),
            SimpleNamespace(id="gpt-z"),
        ])
        chunks = chat_chunks if chat_chunks is not None else [chat_content]
        self.chat_response = iter([
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])
            for content in chunks
        ])
        self.completion_response = completion_response
        self.models = FakeModels(self)
        self.chat = SimpleNamespace(completions=FakeCompletions(self))

    def __enter__(self):
        return self

    def __exit__(self, _exception_type, _exception, _traceback):
        return False


class OpenAIProviderTests(unittest.TestCase):
    def test_creates_connection_after_validating_api_key(self):
        clients = []

        def client_factory(**options):
            client = FakeOpenAIClient(**options)
            clients.append(client)
            return client

        result = OpenAIProvider(client_factory).create_connection(
            provider_id="openai",
            provider_name="OpenAI",
            auth_method="api_key",
            payload={"api_key": "test-key"},
        )

        self.assertTrue(clients[0].models_called)
        self.assertEqual(clients[0].options["api_key"], "test-key")
        self.assertEqual(result.credentials, {"api_key": "test-key"})
        self.assertTrue(result.account_id.startswith("openai-api-key-"))

    def test_lists_unique_sorted_models(self):
        provider = OpenAIProvider(FakeOpenAIClient)

        models = provider.list_models(ProviderConfig(credentials={"api_key": "test-key"}))

        self.assertEqual(models, ["gpt-a", "gpt-z"])

    def test_chats_with_dynamic_model_prompt_and_history(self):
        clients = []

        def client_factory(**options):
            client = FakeOpenAIClient(**options)
            clients.append(client)
            return client

        request = ChatRequest(
            connection_id=1,
            provider="openai",
            model="gpt-test",
            message="Latest question",
            system_prompt="Be concise.",
            history=({"role": "assistant", "content": "Earlier response"},),
        )

        result = OpenAIProvider(client_factory).chat(
            request,
            ProviderConfig(credentials={"api_key": "test-key"}),
        )

        self.assertEqual(result.message, "Test response")
        self.assertEqual(clients[0].chat_call, {
            "model": "gpt-test",
            "messages": [
                {"role": "system", "content": "Be concise."},
                {
                    "role": "assistant",
                    "content": "<|im_start|>assistant\nEarlier response<|im_end|>",
                },
                {
                    "role": "user",
                    "content": "<|im_start|>user\nLatest question<|im_end|>",
                },
            ],
            "stream": True,
        })
        self.assertEqual(clients[0].options["timeout"], 120.0)

    def test_yields_response_chunks(self):
        provider = OpenAIProvider(
            lambda **options: FakeOpenAIClient(chat_chunks=["Test", " response"], **options),
        )

        chunks = list(provider.stream_chat(
            ChatRequest(1, "openai", "gpt-test", "Hello"),
            ProviderConfig(credentials={"api_key": "test-key"}),
        ))

        self.assertEqual(chunks, ["Test", " response"])

    def test_completes_tool_turn_with_discovered_tools(self):
        clients = []
        completion_response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=None,
            tool_calls=[SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(name="read_file", arguments='{"path":"draft.txt"}'),
            )],
        ))])

        def client_factory(**options):
            client = FakeOpenAIClient(completion_response=completion_response, **options)
            clients.append(client)
            return client

        turn = OpenAIProvider(client_factory).complete_chat(
            ChatRequest(1, "openai", "gpt-test", "Read it"),
            ProviderConfig(credentials={"api_key": "test-key"}),
            [{
                "role": "tool",
                "tool_call_id": "previous-call",
                "tool_name": "read_file",
                "content": "Previous result",
            }],
            (ToolDefinition("read_file", "Read a file", {"type": "object"}),),
        )

        self.assertEqual(turn.tool_calls[0].name, "read_file")
        self.assertEqual(turn.tool_calls[0].arguments, {"path": "draft.txt"})
        self.assertEqual(
            clients[0].chat_call["tools"][0]["function"]["name"],
            "read_file",
        )
        self.assertNotIn("tool_name", clients[0].chat_call["messages"][0])
        self.assertFalse(clients[0].chat_call["stream"])

    def test_rejects_empty_response(self):
        provider = OpenAIProvider(lambda **options: FakeOpenAIClient(chat_content=None, **options))

        with self.assertRaisesRegex(LLMError, "empty response") as raised:
            provider.chat(
                ChatRequest(1, "openai", "gpt-test", "Hello"),
                ProviderConfig(credentials={"api_key": "test-key"}),
            )

        self.assertEqual(raised.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
