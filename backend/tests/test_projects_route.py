import unittest

from flask import Flask

from backend.blueprints.projects import projects_bp
from backend.database import Conversation, Message, Project, db


class ProjectRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
        )
        db.init_app(cls.app)
        cls.app.register_blueprint(projects_bp)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def test_creates_project_conversations_and_messages_atomically(self):
        response = self.app.test_client().post(
            "/api/projects",
            json={
                "name": "  Research project  ",
                "description": {
                    "tone": "Academic",
                    "writing_style": "Formal",
                    "academic_level": "Graduate",
                    "language": "English",
                    "essay_type": "Argumentative",
                    "additional_instructions": "  cite recent sources  ",
                },
                "path": "  /tmp/research-project  ",
                "conversations": [
                    {
                        "messages": [
                            {"role": "user", "content": "  Start here  "},
                            {"role": "assistant", "content": "A response"},
                        ]
                    },
                    {"messages": []},
                ],
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload["name"], "Research project")
        self.assertEqual(
            payload["description"],
            "Use an academic tone.\n"
            "Use a formal writing style.\n"
            "Write in English.\n"
            "Write for a graduate academic level.\n"
            "Write an argumentative essay.\n"
            "Also: cite recent sources",
        )
        self.assertEqual(payload["path"], "/tmp/research-project")
        self.assertEqual(len(payload["conversations"]), 2)
        self.assertEqual(
            payload["conversations"][0]["messages"][0]["content"],
            "Start here",
        )

        with self.app.app_context():
            self.assertEqual(Project.query.count(), 1)
            self.assertEqual(Conversation.query.count(), 2)
            self.assertEqual(Message.query.count(), 2)

    def test_get_projects_uses_nested_model_serializers(self):
        client = self.app.test_client()
        created = client.post(
            "/api/projects",
            json={
                "name": "Serialized project",
                "path": "/tmp/serialized-project",
            },
        ).get_json()

        response = client.get("/api/projects/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [created])

    def test_rejects_invalid_nested_message_without_writing_records(self):
        response = self.app.test_client().post(
            "/api/projects",
            json={
                "name": "Invalid project",
                "path": "/tmp/invalid-project",
                "conversations": [
                    {"messages": [{"role": "invalid", "content": "Message"}]}
                ],
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {"error": "message.role must be system, user, or assistant."},
        )
        with self.app.app_context():
            self.assertEqual(Project.query.count(), 0)

    def test_rejects_duplicate_project_name(self):
        client = self.app.test_client()
        payload = {
            "name": "Unique project",
            "path": "/tmp/unique-project",
        }
        self.assertEqual(client.post("/api/projects", json=payload).status_code, 201)

        response = client.post(
            "/api/projects",
            json={**payload, "path": "/tmp/another-project"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json(),
            {"error": "A project with this name or path already exists."},
        )
        with self.app.app_context():
            self.assertEqual(Project.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
