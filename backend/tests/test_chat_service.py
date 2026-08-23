import unittest
from types import SimpleNamespace

from backend.llm import ChatRequest, ChatResult, ChatService, LLMError


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
        self.models_config = None

    def chat(self, request, config):
        self.chat_call = (request, config)
        return ChatResult(message="answer")

    def list_models(self, config):
        self.models_config = config
        return ["gpt-test"]


class FakeOllamaProvider(FakeProvider):
    provider_ids = {"ollama"}
    credential_fields = ()


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
