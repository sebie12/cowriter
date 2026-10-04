import unittest

from flask import Flask

from backend.database import Conversation, Project, ToolCall, db
from backend.services import ConversationService, ToolCallService


class ToolCallServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(cls.app)

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_records_successful_tool_call(self):
        with self.app.app_context():
            project = Project(name="Tool service project")
            conversation = Conversation(project=project)
            db.session.add(project)
            db.session.commit()

            service = ToolCallService()
            tool_call = service.start_tool_call(
                conversation_id=conversation.id,
                provider_call_id="provider-call-1",
                tool_name="read_file",
                input_data={"path": "draft.txt"},
            )
            self.assertEqual(tool_call.status, "pending")

            service.mark_tool_call_running(tool_call.id)
            self.assertEqual(tool_call.status, "running")

            service.complete_tool_call(
                tool_call.id,
                output_data={"content": "Draft"},
            )

            stored = db.session.get(ToolCall, tool_call.id)
            self.assertEqual(stored.status, "completed")
            self.assertEqual(stored.output_data, {"content": "Draft"})
            self.assertIsNotNone(stored.completed_at)

    def test_records_failed_tool_call(self):
        with self.app.app_context():
            project = Project(name="Failed tool project")
            conversation = Conversation(project=project)
            db.session.add(project)
            db.session.commit()

            service = ToolCallService()
            tool_call = service.start_tool_call(
                conversation_id=conversation.id,
                provider_call_id="provider-call-2",
                tool_name="read_file",
                input_data={"path": "missing.txt"},
            )
            service.fail_tool_call(tool_call.id, "File not found.")

            stored = db.session.get(ToolCall, tool_call.id)
            self.assertEqual(stored.status, "failed")
            self.assertEqual(stored.error, "File not found.")
            self.assertIsNotNone(stored.completed_at)

    def test_reuses_or_creates_project_conversation(self):
        with self.app.app_context():
            project = Project(name="Conversation project")
            db.session.add(project)
            db.session.commit()

            service = ConversationService()
            first = service.get_or_create_for_project(project.id)
            second = service.get_or_create_for_project(project.id)

            self.assertEqual(first.id, second.id)
            self.assertEqual(Conversation.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
