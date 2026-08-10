---
name: search-scholar
description: Search Semantic Scholar for academic papers by keyword or title and return citation metadata + abstract. Use when asked to look up a paper, check citation counts, retrieve an abstract, find who cites a paper, or search academic literature for a topic. Prefer Semantic Scholar over Google Scholar (open API, no scraping, no block risk). Trigger on phrases like "search scholar for", "find papers on", "how many citations does", "who cites X", "look up paper", "abstract for", "citation metadata for", "search academic literature for", or any request to query academic paper databases.
---

# Semantic Scholar Search Skill

The [Semantic Scholar Academic Graph API](https://api.semanticscholar.org) is the primary search backend — open, no-scraping, no block risk. For arXiv-specific lookups (by arXiv ID) use [[search-arxiv]] instead; this skill handles keyword, title, and citation queries.

Existing MCP server options (adopt/cite if already configured):
- **scholar-mcp** (mathcity built-in) — FastMCP stdio server wrapping the S2 API. Source: `mathcity/subdomains/proof-assist/mcp/scholar/`. Install: see §Setup.
- Community alternatives: search `uvx semantic-scholar-mcp` or similar; verify source before installing.

## Setup (one-time, requires human approval)

```bash
# 1. Install the mathcity scholar-mcp server
cd <mathcity-pack-root>/subdomains/proof-assist/mcp/scholar
pip install -e .

# 2. Wire it to Claude
claude mcp add --transport stdio scholar -- python -m scholar_mcp.server

# 3. (Optional) Raise rate limits with a free API key
# Apply at: https://www.semanticscholar.org/product/api#api-key-form
# Then set: export SEMANTIC_SCHOLAR_API_KEY=<your-key>
```

Verify: `claude mcp list` should show `scholar: ✓ Connected`.

## Primary path: scholar MCP server

If `mcp__scholar__search_papers` is available, call it directly:

```
mcp__scholar__search_papers(query="The Basic Theory of Clifford-Bianchi Groups", limit=5)
```

Returns `{total, results: [{paperId, title, authors, year, citationCount, abstract, doi, arxivId, url}]}`.

## Direct API path (no MCP required)

Use WebFetch or Bash to call the REST API:

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=Clifford+Bianchi+Groups&fields=title,authors,year,citationCount,abstract,externalIds&limit=5"
```

Or in a skill with WebFetch:
- URL: `https://api.semanticscholar.org/graph/v1/paper/search?query=<URL-encoded>&fields=title,authors,year,citationCount,abstract,externalIds&limit=10`
- Returns JSON: `{total, data: [{paperId, title, authors, year, citationCount, abstract, externalIds}]}`
- `authors` is an array of `{authorId, name}` objects
- `externalIds` contains `DOI`, `ArXiv`, `PubMed`, etc.

**PASS test**: query `"The Basic Theory of Clifford-Bianchi Groups"` → `total > 0`, first result has correct title, `citationCount ≥ 0`, non-empty `authors`.
**FAIL test / rate limit**: `{"message": "Too Many Requests..."}` — wait 60s or supply `x-api-key` header.

## Available MCP tools

| Tool | Purpose |
|------|---------|
| `mcp__scholar__search_papers(query, limit, offset)` | Keyword/title search → metadata + abstract |
| `mcp__scholar__get_paper(paper_id)` | Fetch by S2 paperId, `DOI:10.x/y`, or `ArXiv:2101.00001` |
| `mcp__scholar__get_citations(paper_id, limit)` | Papers that cite a given paper |
| `mcp__scholar__search_authors(name, limit)` | Author profiles by name |

`paper_id` accepts prefixed forms: `DOI:10.1007/s00222-016-0660-8`, `ArXiv:2101.00001`, `PMID:12345678`, or a bare Semantic Scholar hex ID.

## Standard workflow

1. **Search** — `search_papers(query, limit=10)` or direct API call
2. **Pick result** — match title/authors against expected paper; check `citationCount` as a sanity signal
3. **Fetch details** — `get_paper(paperId)` for `referenceCount`, open-access status, or DOI
4. **Citation tree** — `get_citations(paperId, limit=20)` for citing papers
5. **For arXiv papers** — switch to [[search-arxiv]] for BibTeX or PDF links

## Rate limits

- **Unauthenticated**: ~100 requests per 5 minutes. Sufficient for interactive use; city agents should cache results.
- **With API key**: 1000+ req/5min. Apply free at https://www.semanticscholar.org/product/api#api-key-form

## Example queries

| Goal | Query |
|------|-------|
| Find paper by title | `search_papers("Fermat's Last Theorem Wiles", limit=3)` |
| Clifford-Bianchi paper | `search_papers("Basic Theory Clifford-Bianchi Groups", limit=3)` |
| Citation count for a paper | `get_paper("DOI:10.1007/s00222-016-0660-8")` |
| Who cites a paper | `get_citations("205d6b942dbe9d1d5c3e6cac7d2b36c3a5d1d1d5", limit=20)` |
| Search by author name | `search_authors("Andrew Wiles", limit=5)` |

## Relationship to other proof-assist skills

- [[search-arxiv]] — arXiv ID or keyword → PDF + BibTeX. Prefer for preprints; use both if needed.
- [[search-mathlib]] — Lean 4 declaration search via Loogle. For formalization, not bibliography.
