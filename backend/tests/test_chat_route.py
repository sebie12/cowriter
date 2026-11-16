import json
import unittest

from flask import Flask

from backend.blueprints.chat import chat_bp
from backend.llm import LLMError


class FakeChatService:
    def __init__(self):
        self.request = None
        self.error = None

    def stream_chat(self, request):
        self.request = request
        if self.error:
            raise self.error
        return iter([
            {"type": "assistant_start", "id": "assistant-1", "created_at": "2026-09-19T10:00:00Z"},
            {"type": "assistant_delta", "id": "assistant-1", "content": "provider "},
            {"type": "assistant_delta", "id": "assistant-1", "content": "response"},
            {"type": "assistant_end", "id": "assistant-1", "finished_at": "2026-09-19T10:00:01Z"},
        ])


class FakeChatHistory:
    def __init__(self):
        self.messages = []

    def add_message(self, project_id, role, content, created_at=None):
        self.messages.append((project_id, role, content))


class ChatHistoryRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.service = FakeChatService()
        self.history = FakeChatHistory()
        self.app.extensions["chat_service"] = self.service
        self.app.extensions["chat_history"] = self.history
        self.app.register_blueprint(chat_bp)
        self.client = self.app.test_client()
        self.payload = {
            "connection_id": 4,
            "project_id": 9,
            "provider": "openai",
            "model": "gpt-test",
            "message": " Latest question ",
        }

    def test_saves_the_user_message_and_each_finished_reply(self):
        response = self.client.post("/api/chat", json=self.payload)
        response.get_data()

        self.assertEqual(self.history.messages, [
            (9, "user", "Latest question"),
            (9, "assistant", "provider response"),
        ])

    def test_saves_a_reply_cut_short_by_an_error(self):
        def failing_stream(_request):
            yield {"type": "assistant_start", "id": "a", "created_at": "2026-09-19T10:00:00Z"}
            yield {"type": "assistant_delta", "id": "a", "content": "half an"}
            raise LLMError("Provider stopped.", 502)

        self.service.stream_chat = failing_stream
        response = self.client.post("/api/chat", json=self.payload)
        lines = [json.loads(line) for line in response.get_data(as_text=True).splitlines()]

        self.assertEqual(lines[-1], {"type": "error", "error": "Provider stopped."})
        self.assertEqual(self.history.messages[-1], (9, "assistant", "half an"))

    def test_saves_a_reply_the_user_stopped(self):
        response = self.client.post("/api/chat", json=self.payload)
        stream = iter(response.response)
        next(stream)
        next(stream)
        response.close()

        self.assertEqual(self.history.messages, [
            (9, "user", "Latest question"),
            (9, "assistant", "provider"),
        ])

    def test_rejected_request_saves_nothing(self):
        self.service.error = LLMError("Provider is not connected.", 409)

        response = self.client.post("/api/chat", json=self.payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.history.messages, [])

    def test_chat_without_project_saves_nothing(self):
        payload = {key: value for key, value in self.payload.items() if key != "project_id"}

        self.client.post("/api/chat", json=payload).get_data()

        self.assertEqual(self.history.messages, [])


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
            "project_id": 9,
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
        self.assertEqual(response.content_type, "application/x-ndjson")
        self.assertEqual(
            [json.loads(line) for line in response.get_data(as_text=True).splitlines()],
            [
                {"type": "assistant_start", "id": "assistant-1", "created_at": "2026-09-19T10:00:00Z"},
                {"type": "assistant_delta", "id": "assistant-1", "content": "provider "},
                {"type": "assistant_delta", "id": "assistant-1", "content": "response"},
                {"type": "assistant_end", "id": "assistant-1", "finished_at": "2026-09-19T10:00:01Z"},
                {"type": "done"},
            ],
        )
        self.assertEqual(self.service.request.provider, "openai")
        self.assertEqual(self.service.request.project_id, 9)
        self.assertEqual(self.service.request.message, "Latest question")
        self.assertEqual(self.service.request.system_prompt, "Be concise.")
        self.assertEqual(self.service.request.history[0]["content"], "Earlier question")

    def test_builds_system_prompt_from_project_context(self):
        response = self.client.post("/api/chat", json={
            "connection_id": 4,
            "provider": "openai",
            "model": "gpt-test",
            "message": "Help me outline this essay.",
            "title": "Battery usage report",
            "description": "Use an academic tone.",
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'The essay title is "Battery usage report".',
            self.service.request.system_prompt,
        )
        self.assertIn(
            "Follow these project instructions:\nUse an academic tone.",
            self.service.request.system_prompt,
        )

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
