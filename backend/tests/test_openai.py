import unittest
from types import SimpleNamespace

from backend.auth.providers.Openai import OpenAIProvider
from backend.llm import ChatRequest, LLMError, ProviderConfig


class FakeCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, **options):
        self.client.chat_call = options
        return self.client.chat_response


class FakeModels:
    def __init__(self, client):
        self.client = client

    def list(self):
        self.client.models_called = True
        return self.client.models_response


class FakeOpenAIClient:
    def __init__(self, chat_content="Test response", **options):
        self.options = options
        self.chat_call = None
        self.models_called = False
        self.models_response = SimpleNamespace(data=[
            SimpleNamespace(id="gpt-z"),
            SimpleNamespace(id="gpt-a"),
            SimpleNamespace(id="gpt-z"),
        ])
        self.chat_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=chat_content))],
        )
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
                {"role": "assistant", "content": "Earlier response"},
                {"role": "user", "content": "Latest question"},
            ],
        })
        self.assertEqual(clients[0].options["timeout"], 120.0)

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
