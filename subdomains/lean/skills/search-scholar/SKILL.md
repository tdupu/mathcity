---
name: search-scholar
description: Search Semantic Scholar for papers by keyword or title and return citation metadata and abstracts. Use for paper lookup, citation counts, abstracts, citing papers, or academic literature searches. Prefer its API over scraping Google Scholar.
---

# Semantic Scholar Search Skill

The [Semantic Scholar Academic Graph API](https://api.semanticscholar.org) is the primary backend; it can throttle requests. Use [[search-arxiv]] for arXiv IDs.

Use configured MCP servers:

- **scholar-mcp** — built-in FastMCP stdio wrapper at `mathcity/subdomains/lean/mcp/scholar/`; see §Setup.
- Community alternatives: search `uvx semantic-scholar-mcp` or similar; verify source before installing.

## Setup (one-time, requires human approval)

```bash
# 1. Install the mathcity scholar-mcp server
cd <mathcity-pack-root>/subdomains/lean/mcp/scholar
pip install -e .

# 2. Wire it to Claude
claude mcp add --transport stdio scholar -- python -m scholar_mcp.server

# 3. (Optional) Request an individual API quota
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
The built-in formatter truncates abstracts to 800 characters and omits
`referenceCount`, including in `get_paper`. For complete abstracts or reference
counts, use the REST detail path below; a `fields` override cannot fix formatting.

## Direct API path (no MCP required)

Use WebFetch or Bash to call the REST API:

```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=Clifford+Bianchi+Groups&fields=title,authors,year,citationCount,abstract,externalIds&limit=5"
```

WebFetch can use the same endpoint; URL-encode the complete query value.

- Returns JSON: `{total, data: [{paperId, title, authors, year, citationCount, abstract, externalIds}]}`
- `authors` is an array of `{authorId, name}` objects
- `externalIds` contains `DOI`, `ArXiv`, `PubMed`, etc.

**PASS test**: query `"The Basic Theory of Clifford-Bianchi Groups"` → `total > 0`, first result has correct title, `citationCount ≥ 0`, non-empty `authors`.

For complete abstracts or reference counts, GET
`https://api.semanticscholar.org/graph/v1/paper/<paperId>?fields=title,authors,abstract,referenceCount,isOpenAccess,externalIds`.
Use the matched S2 ID. Validate HTTP status and JSON; return the untruncated
`abstract` and `referenceCount`, reporting null or unavailable fields explicitly.
HTTP 429 or MCP `rate_limited` requires backoff (§Rate limits), not an empty-result claim.

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
3. **Fetch details** — `get_paper(paperId)` for open-access status or DOI; REST details for complete abstracts or `referenceCount`
4. **Citation tree** — `get_citations(paperId, limit=20)` for citing papers
5. **For arXiv papers** — switch to [[search-arxiv]] for BibTeX or PDF links

## Rate limits

Anonymous users share capacity; keys have assigned quotas. Consult the
[official guidance](https://webflow.semanticscholar.org/product/api/tutorial)
for current limits. Cache results, pace requests and use `x-api-key` when available.
On 429, honor `Retry-After` if present and back off with bounded retries; report
persistent throttling. A key or fixed wait does not guarantee success.

## Example queries

| Goal | Query |
|------|-------|
| Citation count for a paper | `get_paper("DOI:10.1007/s00222-016-0660-8")` |
| Who cites a paper | `get_citations("205d6b942dbe9d1d5c3e6cac7d2b36c3a5d1d1d5", limit=20)` |
| Search by author name | `search_authors("Andrew Wiles", limit=5)` |

## Relationship to other lean-subdomain skills

- [[search-arxiv]] — arXiv ID or keyword → PDF + BibTeX. Prefer for preprints; use both if needed.
- [[search-mathlib]] — Lean 4 declaration search via Loogle. For formalization, not bibliography.
