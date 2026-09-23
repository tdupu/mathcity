"""FastMCP server for Semantic Scholar academic paper search.

Wraps the Semantic Scholar Academic Graph API (https://api.semanticscholar.org).
No API key required for basic use (100 req/5min unauthenticated, more with key).
Set SEMANTIC_SCHOLAR_API_KEY to use your key for higher rate limits.
"""

import asyncio
import os
import sys
import time
from typing import Any

import requests
from fastmcp import FastMCP

BASE_URL = "https://api.semanticscholar.org/graph/v1"
PAPER_FIELDS = "paperId,title,authors,year,citationCount,referenceCount,abstract,externalIds,url,isOpenAccess,influentialCitationCount"
AUTHOR_FIELDS = "authorId,name,affiliations,homepage,paperCount,citationCount,hIndex"

mcp = FastMCP(
    name="Scholar",
    instructions="""
Semantic Scholar academic paper search. Use search_papers for keyword/title queries.
Prefer search_papers over get_paper unless you have a specific Semantic Scholar paperId or DOI.
""",
)

_session = requests.Session()
_session.headers.update({"User-Agent": "scholar-mcp/0.1.0 (mathcity academic search)"})
_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
if _api_key:
    _session.headers["x-api-key"] = _api_key

_last_request_time: float = 0.0
_MIN_REQUEST_INTERVAL = 0.5  # seconds between requests (2/s default rate)


def _throttle() -> None:
    global _last_request_time
    elapsed = time.monotonic() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _s2_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    _throttle()
    resp = _session.get(f"{BASE_URL}{path}", params=params, timeout=15)
    if resp.status_code == 429:
        return {"error": "rate_limited", "message": "Rate limit hit. Wait 60s or supply SEMANTIC_SCHOLAR_API_KEY."}
    resp.raise_for_status()
    return resp.json()


def _fmt_paper(p: dict[str, Any]) -> dict[str, Any]:
    authors = [a.get("name", "") for a in p.get("authors", [])]
    external = p.get("externalIds") or {}
    return {
        "paperId": p.get("paperId", ""),
        "title": p.get("title", ""),
        "authors": authors,
        "year": p.get("year"),
        "citationCount": p.get("citationCount"),
        "influentialCitationCount": p.get("influentialCitationCount"),
        "abstract": (p.get("abstract") or "")[:800] if p.get("abstract") else None,
        "doi": external.get("DOI"),
        "arxivId": external.get("ArXiv"),
        "url": p.get("url", ""),
        "isOpenAccess": p.get("isOpenAccess"),
    }


@mcp.tool(
    name="search_papers",
    description="Search Semantic Scholar for academic papers by keyword or title. Returns citation metadata and abstracts.",
)
async def search_papers(
    query: str,
    limit: int = 10,
    offset: int = 0,
    fields: str | None = None,
) -> dict[str, Any]:
    """Search academic papers by keyword or title.

    Args:
        query: Search query — paper title, keywords, or author name
        limit: Number of results (1-100, default 10)
        offset: Pagination offset
        fields: Comma-separated Semantic Scholar fields to include (overrides default set)

    Returns:
        {total, results: [{paperId, title, authors, year, citationCount, abstract, doi, arxivId, url}]}
    """
    params: dict[str, Any] = {
        "query": query,
        "limit": max(1, min(limit, 100)),
        "offset": max(0, offset),
        "fields": fields or PAPER_FIELDS,
    }
    data = _s2_get("/paper/search", params)
    if "error" in data:
        return data
    results = [_fmt_paper(p) for p in data.get("data", [])]
    return {"total": data.get("total", 0), "offset": offset, "results": results}


@mcp.tool(
    name="get_paper",
    description="Fetch full metadata for a specific paper by Semantic Scholar paperId, DOI, or ArXiv ID.",
)
async def get_paper(
    paper_id: str,
    fields: str | None = None,
) -> dict[str, Any]:
    """Fetch paper details by ID.

    Args:
        paper_id: Semantic Scholar paperId, or prefixed ID:
                  DOI:10.xxx/yyy, ArXiv:2101.00001, PMID:12345678
        fields: Comma-separated fields to include (overrides default)

    Returns:
        Paper metadata dict with the same shape as search_papers results.
    """
    params = {"fields": fields or PAPER_FIELDS}
    data = _s2_get(f"/paper/{paper_id}", params)
    if "error" in data:
        return data
    return _fmt_paper(data)


@mcp.tool(
    name="get_citations",
    description="Fetch papers that cite a given paper (cited-by list). Returns up to 100 citing papers.",
)
async def get_citations(
    paper_id: str,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Get papers that cite a given paper.

    Args:
        paper_id: Semantic Scholar paperId or DOI:/ArXiv: prefixed ID
        limit: Number of citing papers to return (1-100, default 20)
        offset: Pagination offset

    Returns:
        {total, results: [{paperId, title, authors, year, citationCount, ...}]}
    """
    params = {
        "fields": "paperId,title,authors,year,citationCount,abstract,externalIds,url",
        "limit": max(1, min(limit, 100)),
        "offset": max(0, offset),
    }
    data = _s2_get(f"/paper/{paper_id}/citations", params)
    if "error" in data:
        return data
    results = [_fmt_paper(c.get("citingPaper", c)) for c in data.get("data", [])]
    return {"total": data.get("total", 0), "offset": offset, "results": results}


@mcp.tool(
    name="search_authors",
    description="Search Semantic Scholar for author profiles by name.",
)
async def search_authors(
    name: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Search for author profiles.

    Args:
        name: Author name to search
        limit: Number of results (1-20, default 5)

    Returns:
        {total, results: [{authorId, name, affiliations, paperCount, citationCount, hIndex}]}
    """
    params = {
        "query": name,
        "limit": max(1, min(limit, 20)),
        "fields": AUTHOR_FIELDS,
    }
    data = _s2_get("/author/search", params)
    if "error" in data:
        return data
    results = [
        {
            "authorId": a.get("authorId", ""),
            "name": a.get("name", ""),
            "affiliations": a.get("affiliations", []),
            "homepage": a.get("homepage"),
            "paperCount": a.get("paperCount"),
            "citationCount": a.get("citationCount"),
            "hIndex": a.get("hIndex"),
        }
        for a in data.get("data", [])
    ]
    return {"total": data.get("total", 0), "results": results}


async def async_main() -> None:
    await mcp.run_async(transport="stdio")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
