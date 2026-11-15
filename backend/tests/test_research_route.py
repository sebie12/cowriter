import io
import json
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from flask import Flask

from backend.blueprints.research import research_bp
from backend.services.openalex import OpenAlexClient, normalize_work, rebuild_abstract


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


WORK = {
    "id": "https://openalex.org/W2741809807",
    "display_name": " Attention Is All You Need ",
    "publication_year": 2017,
    "authorships": [
        {"author": {"display_name": "Ashish Vaswani"}},
        {"author": {"display_name": ""}},
        {"author": None},
    ],
    "primary_location": {"source": {"display_name": "NeurIPS"}},
    "abstract_inverted_index": {"Transformers": [0], "attention.": [2], "use": [1]},
    "cited_by_count": 100,
    "doi": "https://doi.org/10.48550/arXiv.1706.03762",
    "open_access": {"oa_url": "https://arxiv.org/abs/1706.03762"},
    "best_oa_location": {"pdf_url": "https://arxiv.org/pdf/1706.03762"},
}


class OpenAlexClientTests(unittest.TestCase):
    def test_normalizes_works_and_skips_invalid_records(self):
        captured = []
        client = OpenAlexClient(
            api_key="secret",
            opener=opener_returning(
                {"meta": {"count": 45}, "results": [WORK, {"id": "https://openalex.org/W1"}] + [WORK] * 18},
                captured,
            ),
        )

        result = client.search("  attention  ", offset=0)

        self.assertEqual(result["total"], 45)
        self.assertEqual(result["next"], 20)
        paper = result["papers"][0]
        self.assertEqual(paper["paper_id"], "W2741809807")
        self.assertEqual(paper["title"], "Attention Is All You Need")
        self.assertEqual(paper["authors"], ["Ashish Vaswani"])
        self.assertEqual(paper["venue"], "NeurIPS")
        self.assertEqual(paper["abstract"], "Transformers use attention.")
        self.assertIsNone(paper["tldr"])
        self.assertEqual(paper["doi"], "10.48550/arXiv.1706.03762")
        self.assertEqual(paper["url"], "https://openalex.org/W2741809807")
        self.assertEqual(paper["pdf_url"], "https://arxiv.org/pdf/1706.03762")
        self.assertEqual(len(result["papers"]), 19)

        params = parse_qs(urlparse(captured[0].full_url).query)
        self.assertEqual(params["search"], ["attention"])
        self.assertEqual(params["page"], ["1"])
        self.assertEqual(params["per-page"], ["20"])
        self.assertEqual(params["api_key"], ["secret"])

    def test_offsets_map_to_pages_and_last_page_has_no_next(self):
        captured = []
        client = OpenAlexClient(
            api_key="",
            opener=opener_returning({"meta": {"count": 45}, "results": [WORK] * 5}, captured),
        )
        result = client.search("llm", offset=40)
        self.assertEqual(parse_qs(urlparse(captured[0].full_url).query)["page"], ["3"])
        self.assertNotIn("api_key", captured[0].full_url)
        self.assertIsNone(result["next"])

    def test_rebuild_abstract_handles_missing_index(self):
        self.assertIsNone(rebuild_abstract(None))
        self.assertIsNone(rebuild_abstract({}))
        self.assertEqual(rebuild_abstract({"b": [1], "a": [0, 2]}), "a b a")

    def test_normalize_falls_back_to_open_access_url(self):
        work = {**WORK, "best_oa_location": None, "doi": None}
        paper = normalize_work(work)
        self.assertEqual(paper["pdf_url"], "https://arxiv.org/abs/1706.03762")
        self.assertIsNone(paper["doi"])

    def test_rejects_offsets_past_the_paging_limit(self):
        client = OpenAlexClient(api_key="", opener=opener_returning({}))
        with self.assertRaises(Exception) as raised:
            client.search("llm", offset=10_000)
        self.assertEqual(raised.exception.status_code, 400)


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
        client = FakeResearchClient(result={"total": 0, "offset": 20, "next": None, "papers": []})
        response = self.make_app(client).test_client().get("/api/research/search?q=llm&offset=20")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.calls, [("llm", 20)])

    def test_empty_query_is_rejected_by_real_client(self):
        app = self.make_app(OpenAlexClient(api_key="", opener=opener_returning({})))
        response = app.test_client().get("/api/research/search?q=%20")
        self.assertEqual(response.status_code, 400)

    def test_rate_limit_passes_through(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

        app = self.make_app(OpenAlexClient(api_key="", opener=opener))
        response = app.test_client().get("/api/research/search?q=llm")
        self.assertEqual(response.status_code, 429)
        self.assertIn("rate limiting", response.get_json()["error"])

    def test_invalid_offset_is_rejected(self):
        app = self.make_app(FakeResearchClient())
        self.assertEqual(app.test_client().get("/api/research/search?q=a&offset=x").status_code, 400)
        self.assertEqual(app.test_client().get("/api/research/search?q=a&offset=-1").status_code, 400)


if __name__ == "__main__":
    unittest.main()
