# scholar-mcp

MCP server wrapping the [Semantic Scholar Academic Graph API](https://api.semanticscholar.org) — academic paper search with citation metadata and abstracts. No scraping; open API with no block risk.

## Install

```bash
pip install -e .
```

## Configure

```bash
claude mcp add --transport stdio scholar -- python -m scholar_mcp.server
```

Optionally, set a free API key for higher rate limits (100 req/5min unauthenticated → 1000+):

```bash
export SEMANTIC_SCHOLAR_API_KEY=<your-key>
# Apply at: https://www.semanticscholar.org/product/api#api-key-form
```

## Tools

| Tool | Description |
|------|-------------|
| `search_papers(query, limit, offset)` | Keyword / title search → metadata + abstract |
| `get_paper(paper_id)` | Fetch by S2 paperId, `DOI:10.x/y`, or `ArXiv:2101.00001` |
| `get_citations(paper_id, limit)` | Papers that cite a given paper |
| `search_authors(name, limit)` | Author profiles by name |

## Example

```
search_papers("The Basic Theory of Clifford-Bianchi Groups", limit=5)
get_paper("DOI:10.1007/s00222-016-0660-8")
get_citations("paperId123abc", limit=20)
```

## Rate limits

- **Unauthenticated**: ~100 requests per 5 minutes (shared IP pool)
- **With API key**: 1000+ req/5min (apply free at the link above)
- The server adds a 0.5s inter-request delay by default to avoid 429s
