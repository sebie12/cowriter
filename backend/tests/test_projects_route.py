import unittest

from flask import Flask

from backend.blueprints.projects import projects_bp
from backend.database import Conversation, Essay, Message, Project, db


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

    def test_creates_project_essay_conversations_and_messages_atomically(self):
        response = self.app.test_client().post(
            "/api/projects",
            json={
                "name": "  Research project  ",
                "description": "  Project description  ",
                "essay": {"title": "  Research essay  "},
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
        self.assertEqual(payload["description"], "Project description")
        self.assertEqual(payload["essay"]["title"], "Research essay")
        self.assertEqual(len(payload["conversations"]), 2)
        self.assertEqual(
            payload["conversations"][0]["messages"][0]["content"],
            "Start here",
        )

        with self.app.app_context():
            self.assertEqual(Project.query.count(), 1)
            self.assertEqual(Essay.query.count(), 1)
            self.assertEqual(Conversation.query.count(), 2)
            self.assertEqual(Message.query.count(), 2)

    def test_get_projects_uses_nested_model_serializers(self):
        client = self.app.test_client()
        created = client.post(
            "/api/projects",
            json={
                "name": "Serialized project",
                "essay": {"title": "Serialized essay"},
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
                "essay": {"title": "Invalid essay"},
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
            "essay": {"title": "Unique essay"},
        }
        self.assertEqual(client.post("/api/projects", json=payload).status_code, 201)

        response = client.post("/api/projects", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json(),
            {"error": "A project with this name already exists."},
        )
        with self.app.app_context():
            self.assertEqual(Project.query.count(), 1)
            self.assertEqual(Essay.query.count(), 1)


if __name__ == "__main__":
    unittest.main()
