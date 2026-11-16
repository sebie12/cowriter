import unittest
from datetime import datetime

from flask import Flask

from backend.blueprints.projects import projects_bp
from backend.database import Conversation, Message, Project, ToolCall, db
from backend.services.chat_history import ChatHistoryService, utc_from_iso


class ChatHistoryTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.app.register_blueprint(projects_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.project = Project(name="Essay")
        self.other = Project(name="Other essay")
        db.session.add_all([self.project, self.other])
        db.session.commit()
        self.history = ChatHistoryService()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.engine.dispose()
        self.context.pop()

    def test_messages_and_tool_calls_come_back_with_the_project(self):
        self.history.add_message(self.project.id, "user", "Rename it", datetime(2026, 11, 16, 14, 0, 0))
        conversation = Conversation.query.filter_by(project_id=self.project.id).one()
        db.session.add(ToolCall(
            conversation_id=conversation.id,
            tool_name="update_project_settings",
            input_data={"title": "New"},
            status="completed",
            created_at=datetime(2026, 11, 16, 14, 0, 1),
        ))
        db.session.commit()
        self.history.add_message(
            self.project.id, "assistant", "Done.", datetime(2026, 11, 16, 14, 0, 2)
        )

        data = self.app.test_client().get(f"/api/projects/{self.project.id}").get_json()

        self.assertEqual(len(data["conversations"]), 1)
        conversation_data = data["conversations"][0]
        self.assertEqual(
            [(message["role"], message["content"]) for message in conversation_data["messages"]],
            [("user", "Rename it"), ("assistant", "Done.")],
        )
        self.assertEqual(conversation_data["tool_calls"][0]["tool_name"], "update_project_settings")

    def test_timeline_interleaves_messages_and_tool_calls_by_time(self):
        self.history.add_message(self.project.id, "user", "Rename it", datetime(2026, 11, 16, 14, 0, 0))
        self.history.add_message(self.project.id, "assistant", "Done.", datetime(2026, 11, 16, 14, 0, 2))
        conversation = Conversation.query.filter_by(project_id=self.project.id).one()
        db.session.add(ToolCall(
            conversation_id=conversation.id, tool_name="update_project_settings", input_data={},
            status="completed", created_at=datetime(2026, 11, 16, 14, 0, 1),
        ))
        db.session.commit()
        self.history.add_message(self.other.id, "user", "Other project")

        timeline = self.history.timeline(self.project.id)

        self.assertEqual(
            [(item["kind"], item.get("content") or item.get("tool_name")) for item in timeline],
            [("message", "Rename it"), ("tool_call", "update_project_settings"), ("message", "Done.")],
        )
        self.assertEqual(self.history.timeline(999), [])

    def test_delete_route_clears_only_that_projects_chat(self):
        self.history.add_message(self.project.id, "user", "Hello")
        self.history.add_message(self.other.id, "user", "Keep me")
        conversation = Conversation.query.filter_by(project_id=self.project.id).one()
        db.session.add(ToolCall(
            conversation_id=conversation.id, tool_name="list_files", input_data={}, status="completed",
        ))
        db.session.commit()

        response = self.app.test_client().delete(f"/api/projects/{self.project.id}/conversation")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Conversation.query.filter_by(project_id=self.project.id).count(), 0)
        self.assertEqual(ToolCall.query.count(), 0)
        self.assertEqual([message.content for message in Message.query.all()], ["Keep me"])

        self.history.add_message(self.project.id, "user", "Fresh start")
        self.assertEqual(Conversation.query.filter_by(project_id=self.project.id).count(), 1)

    def test_delete_route_rejects_unknown_project(self):
        response = self.app.test_client().delete("/api/projects/999/conversation")

        self.assertEqual(response.status_code, 404)

    def test_event_timestamps_become_naive_utc(self):
        self.assertEqual(
            utc_from_iso("2026-11-16T14:00:00.500000Z"),
            datetime(2026, 11, 16, 14, 0, 0, 500000),
        )
        self.assertIsNone(utc_from_iso("not a date").tzinfo)


if __name__ == "__main__":
    unittest.main()
