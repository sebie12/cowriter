import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SEARCH_URL = "https://api.openalex.org/works"
SELECT_FIELDS = (
    "id,display_name,publication_year,authorships,primary_location,"
    "abstract_inverted_index,cited_by_count,doi,open_access,best_oa_location"
)
PAGE_SIZE = 20
MAX_QUERY_LENGTH = 300
# OpenAlex page-based paging stops at 10,000 results.
MAX_RESULTS = 10_000
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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def rebuild_abstract(inverted_index: Any) -> str | None:
    """OpenAlex ships abstracts as {word: [positions]}; put the words back in order."""
    if not isinstance(inverted_index, dict) or not inverted_index:
        return None
    positioned: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        positioned.extend(
            (position, word)
            for position in positions
            if isinstance(position, int) and not isinstance(position, bool)
        )
    if not positioned:
        return None
    positioned.sort()
    return " ".join(word for _, word in positioned)


def _short_id(openalex_id: str) -> str:
    return openalex_id.rstrip("/").rsplit("/", 1)[-1]


def _doi(value: Any) -> str | None:
    doi = _string_or_none(value)
    if doi is None:
        return None
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            return doi[len(prefix):]
    return doi


def normalize_work(raw: Any) -> dict[str, Any] | None:
    """Map an OpenAlex work to Cowriter's paper wire shape."""
    if not isinstance(raw, dict):
        return None
    openalex_id = _string_or_none(raw.get("id"))
    title = _string_or_none(raw.get("display_name"))
    if not openalex_id or not title:
        return None

    authors = []
    for authorship in raw.get("authorships") or ():
        name = _string_or_none(_dict(_dict(authorship).get("author")).get("display_name"))
        if name:
            authors.append(name)

    source = _dict(_dict(raw.get("primary_location")).get("source"))
    pdf_url = (
        _string_or_none(_dict(raw.get("best_oa_location")).get("pdf_url"))
        or _string_or_none(_dict(raw.get("open_access")).get("oa_url"))
    )

    return {
        "paper_id": _short_id(openalex_id),
        "title": title,
        "year": _int_or_none(raw.get("publication_year")),
        "authors": authors,
        "venue": _string_or_none(source.get("display_name")),
        "abstract": rebuild_abstract(raw.get("abstract_inverted_index")),
        "tldr": None,
        "citation_count": _int_or_none(raw.get("cited_by_count")),
        "doi": _doi(raw.get("doi")),
        "url": openalex_id if openalex_id.startswith("https://") else None,
        "pdf_url": pdf_url,
    }


class OpenAlexClient:
    def __init__(
        self,
        api_key: str | None = None,
        opener: Callable[..., Any] | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENALEX_API_KEY")
        self.opener = opener or urlopen

    def search(self, query: str, offset: int = 0) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ResearchError("A search query is required.", 400)
        if len(query) > MAX_QUERY_LENGTH:
            raise ResearchError(f"The search query must be {MAX_QUERY_LENGTH} characters or fewer.", 400)
        # Pages are fixed-size, so snap the offset to the start of a page.
        offset = max(0, offset) // PAGE_SIZE * PAGE_SIZE
        if offset >= MAX_RESULTS:
            raise ResearchError("OpenAlex can only page through the first 10,000 results.", 400)

        params = {
            "search": query,
            "per-page": PAGE_SIZE,
            "page": offset // PAGE_SIZE + 1,
            "select": SELECT_FIELDS,
        }
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{SEARCH_URL}?{urlencode(params)}"
        headers = {"Accept": "application/json", "User-Agent": "cowriter"}

        try:
            with self.opener(Request(url, headers=headers), timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                raise ResearchError(
                    "OpenAlex is rate limiting requests. Try again later, or set OPENALEX_API_KEY.", 429
                ) from error
            if 400 <= error.code < 500:
                raise ResearchError("OpenAlex rejected the search request.", 400) from error
            raise ResearchError("OpenAlex could not complete the search.", 502) from error
        except (URLError, TimeoutError, OSError) as error:
            raise ResearchError("Could not reach OpenAlex.", 502) from error
        except (ValueError, UnicodeDecodeError) as error:
            raise ResearchError("OpenAlex returned an unreadable response.", 502) from error

        if not isinstance(payload, dict):
            raise ResearchError("OpenAlex returned an unreadable response.", 502)

        results = payload.get("results") or ()
        papers = [paper for paper in (normalize_work(raw) for raw in results) if paper is not None]
        total = _int_or_none(_dict(payload.get("meta")).get("count")) or 0
        next_offset = offset + PAGE_SIZE
        has_more = len(results) == PAGE_SIZE and next_offset < min(total, MAX_RESULTS)
        return {
            "total": total,
            "offset": offset,
            "next": next_offset if has_more else None,
            "papers": papers,
        }
