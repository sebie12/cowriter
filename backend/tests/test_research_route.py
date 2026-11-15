import io
import json
import unittest
from urllib.error import HTTPError

from flask import Flask

from backend.blueprints.research import research_bp
from backend.services.semantic_scholar import SemanticScholarClient, normalize_paper


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def opener_returning(payload, captured=None):
    def opener(request, timeout):
        if captured is not None:
            captured.append(request)
        return FakeResponse(json.dumps(payload).encode("utf-8"))
    return opener


class SemanticScholarClientTests(unittest.TestCase):
    def test_normalizes_papers_and_skips_invalid_records(self):
        captured = []
        client = SemanticScholarClient(
            api_key="secret",
            opener=opener_returning({
                "total": 2,
                "offset": 0,
                "next": 20,
                "data": [
                    {
                        "paperId": "abc",
                        "title": " Attention Is All You Need ",
                        "year": 2017,
                        "authors": [{"authorId": "1", "name": "Ashish Vaswani"}, {"name": ""}],
                        "venue": "NeurIPS",
                        "abstract": "Transformers.",
                        "tldr": {"model": "tldr@v2", "text": "A new architecture."},
                        "citationCount": 100,
                        "externalIds": {"DOI": "10.1/xyz"},
                        "url": "https://example.org/abc",
                        "openAccessPdf": {"url": "https://example.org/abc.pdf"},
                    },
                    {"paperId": "missing-title"},
                ],
            }, captured),
        )

        result = client.search("  attention  ", offset=0)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["next"], 20)
        self.assertEqual(len(result["papers"]), 1)
        paper = result["papers"][0]
        self.assertEqual(paper["title"], "Attention Is All You Need")
        self.assertEqual(paper["authors"], ["Ashish Vaswani"])
        self.assertEqual(paper["tldr"], "A new architecture.")
        self.assertEqual(paper["doi"], "10.1/xyz")
        self.assertEqual(paper["pdf_url"], "https://example.org/abc.pdf")
        self.assertIn("query=attention", captured[0].full_url)
        self.assertEqual(captured[0].get_header("X-api-key"), "secret")

    def test_normalize_handles_missing_optional_fields(self):
        paper = normalize_paper({"paperId": "p", "title": "T", "tldr": None, "authors": None})
        self.assertEqual(paper["authors"], [])
        self.assertIsNone(paper["tldr"])
        self.assertIsNone(paper["year"])


class FakeResearchClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def search(self, query, offset=0):
        self.calls.append((query, offset))
        if self.error:
            raise self.error
        return self.result


class ResearchRouteTests(unittest.TestCase):
    def make_app(self, client):
        app = Flask(__name__)
        app.register_blueprint(research_bp)
        app.extensions["research_client"] = client
        return app

    def test_returns_search_results(self):
        client = FakeResearchClient(result={"total": 0, "offset": 5, "next": None, "papers": []})
        response = self.make_app(client).test_client().get("/api/research/search?q=llm&offset=5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.calls, [("llm", 5)])

    def test_empty_query_is_rejected_by_real_client(self):
        app = self.make_app(SemanticScholarClient(api_key="", opener=opener_returning({})))
        response = app.test_client().get("/api/research/search?q=%20")
        self.assertEqual(response.status_code, 400)

    def test_rate_limit_passes_through(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

        app = self.make_app(SemanticScholarClient(api_key="", opener=opener))
        response = app.test_client().get("/api/research/search?q=llm")
        self.assertEqual(response.status_code, 429)
        self.assertIn("rate limiting", response.get_json()["error"])

    def test_invalid_offset_is_rejected(self):
        app = self.make_app(FakeResearchClient())
        self.assertEqual(app.test_client().get("/api/research/search?q=a&offset=x").status_code, 400)
        self.assertEqual(app.test_client().get("/api/research/search?q=a&offset=-1").status_code, 400)


if __name__ == "__main__":
    unittest.main()
