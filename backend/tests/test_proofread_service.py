import json
import unittest

from flask import Flask

from backend.blueprints.projects import projects_bp
from backend.database import Project, Reference, db
from backend.llm.contracts import ChatResult, LLMError
from backend.services.proofread_service import ProofreadService, locate_issues, parse_review


class FakeProvider:
    def __init__(self, reply):
        self.reply = reply
        self.requests = []

    def chat(self, request, config):
        self.requests.append(request)
        return ChatResult(message=self.reply)


class FakeChatService:
    def __init__(self, provider):
        self.provider = provider

    def resolve_provider(self, *, connection_id, requested_provider):
        return self.provider, object()


def review_reply(*issues):
    return json.dumps({"issues": list(issues)})


class ProofreadParsingTests(unittest.TestCase):
    def test_parses_fenced_json(self):
        content = "```json\n" + review_reply({"type": "spelling", "quote": "teh"}) + "\n```"
        self.assertEqual(parse_review(content)[0]["quote"], "teh")

    def test_invalid_json_raises_502(self):
        with self.assertRaises(LLMError) as raised:
            parse_review("I found no problems!")
        self.assertEqual(raised.exception.status_code, 502)

    def test_computes_offsets_and_drops_missing_quotes(self):
        text = "Teh cat sat. Water boils at 50 degrees."
        issues = locate_issues(
            text,
            [
                {"type": "claim", "quote": "Water boils at 50 degrees", "explanation": "False.", "reference_ids": [1, 99, "x"]},
                {"type": "spelling", "quote": "Teh", "suggestion": "The"},
                {"type": "spelling", "quote": "not in text"},
                {"type": "unknown", "quote": "cat"},
            ],
            valid_reference_ids={1},
        )
        self.assertEqual([issue["type"] for issue in issues], ["spelling", "claim"])
        spelling, claim = issues
        self.assertEqual((spelling["start"], spelling["end"]), (0, 3))
        self.assertEqual(spelling["suggestion"], "The")
        self.assertEqual(text[claim["start"]:claim["end"]], "Water boils at 50 degrees")
        self.assertEqual(claim["reference_ids"], [1])

    def test_repeated_quotes_map_in_order(self):
        text = "recieve this and recieve that"
        issues = locate_issues(
            text,
            [{"type": "spelling", "quote": "recieve"}, {"type": "spelling", "quote": "recieve"}],
            set(),
        )
        self.assertEqual([issue["start"] for issue in issues], [0, 17])

    def test_narrows_phrase_spelling_quote_to_the_corrected_word(self):
        text = "This is a well knwon fact."
        issues = locate_issues(
            text, [{"type": "spelling", "quote": "well knwon", "suggestion": "known"}], set()
        )
        self.assertEqual(issues[0]["quote"], "knwon")
        self.assertEqual(issues[0]["suggestion"], "known")

    def test_matches_quotes_with_different_whitespace(self):
        text = "A long\nsentence here."
        issues = locate_issues(text, [{"type": "style", "quote": "long sentence"}], set())
        self.assertEqual(issues[0]["quote"], "long\nsentence")


class ProofreadServiceTests(unittest.TestCase):
    def test_review_without_project_path_uses_plain_chat(self):
        provider = FakeProvider(review_reply({"type": "spelling", "quote": "teh", "suggestion": "the"}))
        service = ProofreadService(FakeChatService(provider))
        issues = service.review(
            connection_id=1,
            provider="openai",
            model="m",
            text="teh end",
            references=[{"id": 4, "title": "Paper", "authors": ["A"], "year": 2020, "tldr": "Summary"}],
        )
        self.assertEqual(issues[0]["start"], 0)
        self.assertIn("[id=4] Paper (2020)", provider.requests[0].system_prompt)

    def test_empty_text_skips_the_model(self):
        provider = FakeProvider("")
        self.assertEqual(
            ProofreadService(FakeChatService(provider)).review(
                connection_id=1, provider="openai", model="m", text="   "
            ),
            [],
        )
        self.assertEqual(provider.requests, [])


class ProofreadRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            TESTING=True,
        )
        db.init_app(self.app)
        self.app.register_blueprint(projects_bp)
        self.provider = FakeProvider(review_reply({"type": "claim", "quote": "Moon is cheese", "reference_ids": []}))
        self.app.extensions["proofread_service"] = ProofreadService(FakeChatService(self.provider))
        with self.app.app_context():
            db.create_all()
            project = Project(name="Thesis", references=[Reference(paper_id="p", title="Lunar geology", authors=[])])
            db.session.add(project)
            db.session.commit()
            self.project_id = project.id

    def test_returns_located_issues(self):
        response = self.app.test_client().post(
            f"/api/projects/{self.project_id}/proofread",
            json={"connection_id": 1, "provider": "openai", "model": "m", "text": "The Moon is cheese."},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        issues = response.get_json()["issues"]
        self.assertEqual((issues[0]["start"], issues[0]["end"]), (4, 18))
        self.assertIn("Lunar geology", self.provider.requests[0].system_prompt)

    def test_validates_payload(self):
        response = self.app.test_client().post(
            f"/api/projects/{self.project_id}/proofread",
            json={"provider": "openai", "model": "m", "text": "x"},
        )
        self.assertEqual(response.status_code, 400)

    def test_unreadable_review_returns_502(self):
        self.provider.reply = "Looks good to me!"
        response = self.app.test_client().post(
            f"/api/projects/{self.project_id}/proofread",
            json={"connection_id": 1, "provider": "openai", "model": "m", "text": "x"},
        )
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
