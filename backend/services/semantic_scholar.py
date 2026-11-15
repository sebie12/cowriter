import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
BASE_FIELDS = "paperId,title,year,authors,venue,abstract,citationCount,externalIds,url,openAccessPdf"
SEARCH_FIELDS = f"{BASE_FIELDS},tldr"
MAX_QUERY_LENGTH = 300
MAX_LIMIT = 50
REQUEST_TIMEOUT_SECONDS = 20


class ResearchError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _string_or_none(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def normalize_paper(raw: Any) -> dict[str, Any] | None:
    """Map a Semantic Scholar paper record to Cowriter's wire shape."""
    if not isinstance(raw, dict):
        return None
    paper_id = _string_or_none(raw.get("paperId"))
    title = _string_or_none(raw.get("title"))
    if not paper_id or not title:
        return None

    authors = [
        author["name"].strip()
        for author in raw.get("authors") or ()
        if isinstance(author, dict) and _string_or_none(author.get("name"))
    ]
    tldr = raw.get("tldr")
    external_ids = raw.get("externalIds") if isinstance(raw.get("externalIds"), dict) else {}
    open_access_pdf = raw.get("openAccessPdf") if isinstance(raw.get("openAccessPdf"), dict) else {}

    return {
        "paper_id": paper_id,
        "title": title,
        "year": _int_or_none(raw.get("year")),
        "authors": authors,
        "venue": _string_or_none(raw.get("venue")),
        "abstract": _string_or_none(raw.get("abstract")),
        "tldr": _string_or_none(tldr.get("text")) if isinstance(tldr, dict) else None,
        "citation_count": _int_or_none(raw.get("citationCount")),
        "doi": _string_or_none(external_ids.get("DOI")),
        "url": _string_or_none(raw.get("url")),
        "pdf_url": _string_or_none(open_access_pdf.get("url")),
    }


class SemanticScholarClient:
    def __init__(
        self,
        api_key: str | None = None,
        opener: Callable[..., Any] | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.opener = opener or urlopen

    def search(self, query: str, offset: int = 0, limit: int = 20) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ResearchError("A search query is required.", 400)
        if len(query) > MAX_QUERY_LENGTH:
            raise ResearchError(f"The search query must be {MAX_QUERY_LENGTH} characters or fewer.", 400)
        offset = max(0, offset)
        limit = min(max(1, limit), MAX_LIMIT)

        try:
            payload = self._fetch(query, offset, limit, SEARCH_FIELDS)
        except ResearchError as error:
            # TLDRs are not offered for every search mode; retry without them before giving up.
            if error.status_code != 400:
                raise
            payload = self._fetch(query, offset, limit, BASE_FIELDS)

        if not isinstance(payload, dict):
            raise ResearchError("Semantic Scholar returned an unreadable response.", 502)

        papers = [
            paper
            for paper in (normalize_paper(raw) for raw in payload.get("data") or ())
            if paper is not None
        ]
        total = _int_or_none(payload.get("total")) or 0
        next_offset = _int_or_none(payload.get("next"))
        return {
            "total": total,
            "offset": offset,
            "next": next_offset,
            "papers": papers,
        }

    def _fetch(self, query: str, offset: int, limit: int, fields: str) -> Any:
        url = f"{SEARCH_URL}?{urlencode({'query': query, 'offset': offset, 'limit': limit, 'fields': fields})}"
        headers = {"Accept": "application/json", "User-Agent": "cowriter"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            with self.opener(Request(url, headers=headers), timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                raise ResearchError(
                    "Semantic Scholar is rate limiting requests. Try again in a moment.", 429
                ) from error
            if 400 <= error.code < 500:
                raise ResearchError("Semantic Scholar rejected the search request.", 400) from error
            raise ResearchError("Semantic Scholar could not complete the search.", 502) from error
        except (URLError, TimeoutError, OSError) as error:
            raise ResearchError("Could not reach Semantic Scholar.", 502) from error
        except (ValueError, UnicodeDecodeError) as error:
            raise ResearchError("Semantic Scholar returned an unreadable response.", 502) from error
