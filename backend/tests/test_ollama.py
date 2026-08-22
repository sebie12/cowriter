import unittest

import ollama

from backend.auth.connections import ProviderConnectionError
from backend.auth.providers.Ollama import OllamaProvider, normalize_ollama_server_url


class FakeClient:
    def __init__(self, host=None, request_error=None, list_response=None, chat_response=None, **options):
        self.host = host
        self.request_error = request_error
        self.list_response = list_response or ollama.ListResponse(models=[])
        self.chat_response = chat_response or ollama.ChatResponse(
            message=ollama.Message(role="assistant", content="Test response"),
        )
        self.options = options
        self.list_called = False
        self.chat_call = None

    def __enter__(self):
        return self

    def __exit__(self, _exception_type, _exception, _traceback):
        return False

    def list(self):
        self.list_called = True
        if self.request_error:
            raise self.request_error
        return self.list_response

    def chat(self, **options):
        self.chat_call = options
        if self.request_error:
            raise self.request_error
        return self.chat_response


class OllamaProviderTests(unittest.TestCase):
    def test_normalizes_localhost(self):
        self.assertEqual(
            normalize_ollama_server_url("http://localhost:11434/"),
            "http://127.0.0.1:11434",
        )

    def test_rejects_non_loopback_hosts(self):
        with self.assertRaisesRegex(ProviderConnectionError, "this computer"):
            normalize_ollama_server_url("http://192.168.1.50:11434")

    def test_rejects_paths_and_credentials(self):
        for url in (
            "http://127.0.0.1:11434/api",
            "http://user:password@127.0.0.1:11434",
        ):
            with self.subTest(url=url), self.assertRaises(ProviderConnectionError):
                normalize_ollama_server_url(url)

    def test_creates_credential_free_connection(self):
        clients = []

        def client_factory(**options):
            client = FakeClient(**options)
            clients.append(client)
            return client

        result = OllamaProvider(client_factory).create_connection(
            provider_id="ollama",
            provider_name="Ollama",
            auth_method="local",
            payload={"server_url": "http://localhost:11434"},
        )

        self.assertEqual(result.endpoint_url, "http://127.0.0.1:11434")
        self.assertEqual(result.credentials, {})
        self.assertEqual(result.account_label, "Ollama at 127.0.0.1:11434")
        self.assertEqual(clients[0].host, "http://127.0.0.1:11434")
        self.assertTrue(clients[0].list_called)
        self.assertEqual(clients[0].options["timeout"], 5.0)
        self.assertFalse(clients[0].options["follow_redirects"])
        self.assertFalse(clients[0].options["trust_env"])

    def test_reports_connection_failures(self):
        provider = OllamaProvider(
            lambda **options: FakeClient(
                request_error=ConnectionError("offline"),
                **options,
            )
        )

        with self.assertRaisesRegex(ProviderConnectionError, "Could not connect") as raised:
            provider.validate_connection("http://127.0.0.1:11434")
        self.assertEqual(raised.exception.status_code, 502)

    def test_lists_unique_sorted_models(self):
        response = ollama.ListResponse(models=[
            ollama.ListResponse.Model(model="qwen3:8b"),
            ollama.ListResponse.Model(model="Gemma3:latest"),
            ollama.ListResponse.Model(model="qwen3:8b"),
            ollama.ListResponse.Model(model=None),
        ])
        provider = OllamaProvider(
            lambda **options: FakeClient(list_response=response, **options),
        )

        self.assertEqual(
            provider.list_models("http://127.0.0.1:11434"),
            ["Gemma3:latest", "qwen3:8b"],
        )

    def test_chats_with_selected_model_and_messages(self):
        clients = []

        def client_factory(**options):
            client = FakeClient(**options)
            clients.append(client)
            return client

        messages = [{"role": "user", "content": "Hello"}]
        content = OllamaProvider(client_factory).chat(
            "http://127.0.0.1:11434",
            "qwen3:8b",
            messages,
        )

        self.assertEqual(content, "Test response")
        self.assertEqual(clients[0].chat_call, {
            "model": "qwen3:8b",
            "messages": messages,
            "stream": False,
        })
        self.assertEqual(clients[0].options["timeout"], 120.0)

    def test_rejects_empty_chat_response(self):
        response = ollama.ChatResponse(
            message=ollama.Message(role="assistant", content=None),
        )
        provider = OllamaProvider(
            lambda **options: FakeClient(chat_response=response, **options),
        )

        with self.assertRaisesRegex(ProviderConnectionError, "empty response") as raised:
            provider.chat(
                "http://127.0.0.1:11434",
                "qwen3:8b",
                [{"role": "user", "content": "Hello"}],
            )
        self.assertEqual(raised.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
