import unittest

from flask import Flask

from backend.blueprints.chat import chat_bp
from backend.llm import ChatResult, LLMError


class FakeChatService:
    def __init__(self):
        self.request = None
        self.error = None

    def chat(self, request):
        self.request = request
        if self.error:
            raise self.error
        return ChatResult(message="provider response")


class ChatRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.service = FakeChatService()
        self.app.extensions["chat_service"] = self.service
        self.app.register_blueprint(chat_bp)
        self.client = self.app.test_client()

    def test_passes_provider_independent_request_to_service(self):
        response = self.client.post("/api/chat", json={
            "connection_id": 4,
            "provider": "openai",
            "model": "gpt-test",
            "message": " Latest question ",
            "system_prompt": " Be concise. ",
            "history": [
                {"role": "user", "content": " Earlier question "},
                {"role": "assistant", "content": "Earlier response"},
            ],
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "provider response"})
        self.assertEqual(self.service.request.provider, "openai")
        self.assertEqual(self.service.request.message, "Latest question")
        self.assertEqual(self.service.request.system_prompt, "Be concise.")
        self.assertEqual(self.service.request.history[0]["content"], "Earlier question")

    def test_returns_service_error(self):
        self.service.error = LLMError("Unsupported chat provider: unknown.", 400)

        response = self.client.post("/api/chat", json={
            "connection_id": 4,
            "provider": "unknown",
            "model": "model",
            "message": "Hello",
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "Unsupported chat provider: unknown."})

    def test_rejects_invalid_history(self):
        response = self.client.post("/api/chat", json={
            "connection_id": 4,
            "provider": "openai",
            "model": "model",
            "message": "Hello",
            "history": [{"role": "system", "content": "Not allowed here"}],
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "history contains an invalid message."})


if __name__ == "__main__":
    unittest.main()
