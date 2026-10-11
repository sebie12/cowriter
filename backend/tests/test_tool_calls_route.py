import unittest
from datetime import datetime, timedelta

from flask import Flask

from backend.blueprints.tool_calls import tool_calls_bp
from backend.database import Conversation, Project, ToolCall, db


class ToolCallsRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
        )
        db.init_app(cls.app)
        cls.app.register_blueprint(tool_calls_bp)
        cls.client = cls.app.test_client()

    def setUp(self):
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_lists_conversation_tool_calls_in_execution_order(self):
        with self.app.app_context():
            project = Project(name="Tool endpoint project")
            conversation = Conversation(project=project)
            called_at = datetime(2026, 9, 19, 10, 0, 0)
            conversation.tool_calls.extend([
                ToolCall(
                    provider_call_id="call-2",
                    tool_name="write_file",
                    input_data={"path": "draft.txt"},
                    status="completed",
                    created_at=called_at + timedelta(seconds=1),
                ),
                ToolCall(
                    provider_call_id="call-1",
                    tool_name="read_file",
                    input_data={"path": "notes.txt"},
                    status="completed",
                    created_at=called_at,
                ),
            ])
            db.session.add(project)
            db.session.commit()
            conversation_id = conversation.id

        response = self.client.get(f"/api/conversations/{conversation_id}/tool-calls")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [tool_call["provider_call_id"] for tool_call in response.get_json()],
            ["call-1", "call-2"],
        )

    def test_returns_empty_list_for_conversation_without_tool_calls(self):
        with self.app.app_context():
            project = Project(name="Empty tool endpoint project")
            conversation = Conversation(project=project)
            db.session.add(project)
            db.session.commit()
            conversation_id = conversation.id

        response = self.client.get(f"/api/conversations/{conversation_id}/tool-calls")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_returns_not_found_for_unknown_conversation(self):
        response = self.client.get("/api/conversations/999/tool-calls")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Conversation not found."})

    def test_old_ambiguous_tool_calls_path_is_not_available(self):
        response = self.client.get("/api/tool-calls/999")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
