import unittest
from datetime import datetime, timedelta

from flask import Flask
from sqlalchemy.exc import IntegrityError

from backend.database import db
from backend.database.models import Conversation, Essay, Message, Project


class ConversationMessageModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
        )
        db.init_app(cls.app)
        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.create_all()

    def test_messages_are_ordered_and_deleted_with_conversation(self):
        with self.app.app_context():
            project = Project(name="Test project")
            project.essay = Essay(title="Test essay")
            conversation = Conversation(project=project)
            created_at = datetime(2026, 8, 23, 10, 0, 0)
            conversation.messages.extend(
                [
                    Message(
                        role="assistant",
                        content="Second",
                        created_at=created_at + timedelta(seconds=1),
                    ),
                    Message(
                        role="user",
                        content="First",
                        created_at=created_at,
                    ),
                ]
            )
            db.session.add(project)
            db.session.commit()

            conversation_id = conversation.id
            message_ids = [message.id for message in conversation.messages]
            self.assertEqual(
                [message.content for message in conversation.messages],
                ["First", "Second"],
            )
            self.assertEqual(
                str(conversation.messages[0]),
                f"Message {message_ids[0]} in Conversation {conversation_id}",
            )

            db.session.delete(conversation)
            db.session.commit()

            self.assertEqual(
                Message.query.filter(Message.id.in_(message_ids)).count(),
                0,
            )

    def test_project_owns_one_essay_and_multiple_conversations(self):
        with self.app.app_context():
            project = Project(
                name="Relationship project",
                essay=Essay(title="Relationship essay"),
                conversations=[Conversation(), Conversation()],
            )
            db.session.add(project)
            db.session.commit()

            self.assertEqual(project.essay.title, "Relationship essay")
            self.assertEqual(len(project.conversations), 2)
            self.assertTrue(
                all(conversation.project is project for conversation in project.conversations)
            )

            db.session.add(Essay(title="Duplicate essay", project_id=project.id))
            with self.assertRaises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_database_project_delete_cascades_to_owned_records(self):
        with self.app.app_context():
            project = Project(
                name="Cascade project",
                essay=Essay(title="Cascade essay"),
                conversations=[
                    Conversation(
                        messages=[Message(role="user", content="Delete me")],
                    )
                ],
            )
            db.session.add(project)
            db.session.commit()

            project_id = project.id
            essay_id = project.essay.id
            conversation_id = project.conversations[0].id
            message_id = project.conversations[0].messages[0].id
            db.session.execute(
                db.delete(Project).where(Project.id == project_id)
            )
            db.session.commit()

            self.assertIsNone(db.session.get(Essay, essay_id))
            self.assertIsNone(db.session.get(Conversation, conversation_id))
            self.assertIsNone(db.session.get(Message, message_id))


if __name__ == "__main__":
    unittest.main()
