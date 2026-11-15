import unittest

from flask import Flask

from backend.blueprints.projects import projects_bp
from backend.database import Project, Reference, db


PAPER = {
    "paper_id": "abc",
    "title": "Attention Is All You Need",
    "year": 2017,
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "venue": "NeurIPS",
    "abstract": "Transformers.",
    "tldr": "A new architecture.",
    "citation_count": 100,
    "doi": "10.1/xyz",
    "url": "https://example.org/abc",
    "pdf_url": None,
}


class ReferenceRouteTests(unittest.TestCase):
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

    def setUp(self):
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            project = Project(name="Thesis")
            db.session.add(project)
            db.session.commit()
            self.project_id = project.id
        self.client = self.app.test_client()

    def test_saves_lists_and_deletes_references(self):
        created = self.client.post(f"/api/projects/{self.project_id}/references", json=PAPER)
        self.assertEqual(created.status_code, 201)
        reference = created.get_json()
        self.assertEqual(reference["authors"], PAPER["authors"])
        self.assertIsNotNone(reference["created_at"])

        listed = self.client.get(f"/api/projects/{self.project_id}/references").get_json()
        self.assertEqual([item["paper_id"] for item in listed], ["abc"])

        deleted = self.client.delete(f"/api/projects/{self.project_id}/references/{reference['id']}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/projects/{self.project_id}/references").get_json(), [])

    def test_duplicate_paper_returns_conflict_with_existing_record(self):
        self.client.post(f"/api/projects/{self.project_id}/references", json=PAPER)
        duplicate = self.client.post(f"/api/projects/{self.project_id}/references", json=PAPER)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.get_json()["reference"]["paper_id"], "abc")

    def test_rejects_invalid_reference(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/references",
            json={**PAPER, "authors": "not a list"},
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.post(f"/api/projects/{self.project_id}/references", json={"title": "x"})
        self.assertEqual(response.status_code, 400)

    def test_delete_checks_project_ownership(self):
        reference_id = self.client.post(
            f"/api/projects/{self.project_id}/references", json=PAPER
        ).get_json()["id"]
        with self.app.app_context():
            other = Project(name="Other")
            db.session.add(other)
            db.session.commit()
            other_id = other.id
        response = self.client.delete(f"/api/projects/{other_id}/references/{reference_id}")
        self.assertEqual(response.status_code, 404)

    def test_deleting_project_removes_references(self):
        self.client.post(f"/api/projects/{self.project_id}/references", json=PAPER)
        self.assertEqual(self.client.delete(f"/api/projects/{self.project_id}").status_code, 200)
        with self.app.app_context():
            self.assertEqual(Reference.query.count(), 0)

    def test_saves_draft(self):
        draft = {"type": "doc", "content": [{"type": "paragraph"}]}
        response = self.client.put(f"/api/projects/{self.project_id}/draft", json={"draft": draft})
        self.assertEqual(response.status_code, 200)
        project = self.client.get(f"/api/projects/{self.project_id}").get_json()
        self.assertEqual(project["draft"], draft)

    def test_rejects_invalid_draft(self):
        response = self.client.put(f"/api/projects/{self.project_id}/draft", json={"draft": "text"})
        self.assertEqual(response.status_code, 400)
        response = self.client.put(f"/api/projects/{self.project_id}/draft", json={})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
