---
name: search-arxiv
description: >
  Search arXiv by paper ID or keyword and return title, abstract, authors, and BibTeX.
  Use when asked to look up an arXiv paper, fetch metadata for a citation, check what
  a paper is about, generate BibTeX for an arXiv ID, or find papers on a topic.
  Trigger on phrases like "look up arXiv 2407.19122", "BibTeX for this paper",
  "search arXiv for X", "what is arXiv:XXXX", "fetch metadata for", "cite this paper",
  or any request to retrieve or cite arXiv papers by ID or keyword.
---

# search-arxiv

Fetch paper metadata (title / abstract / authors / BibTeX) from arXiv.

**Adopted upstream:** [`blazickjp/arxiv-mcp-server`](https://github.com/blazickjp/arxiv-mcp-server)
(Python, 3 k stars, v0.5.0) — the recommended MCP server for full-paper download and
reading. The skill below uses the arXiv Atom API directly for lightweight metadata
retrieval; install the MCP server for full-text access (see §MCP enhancement).

---

## Step 1 — Identify the query type

- **arXiv ID** (e.g. `2407.19122`, `math/0603460`, `2407.19122v2`): go to Step 2a.
- **Keyword / author / title**: go to Step 2b.

---

## Step 2a — Fetch by arXiv ID

WebFetch the Atom endpoint:

```
https://export.arxiv.org/api/query?id_list=<ID>
```

Example: `https://export.arxiv.org/api/query?id_list=2407.19122`

Prompt: *"Extract from this Atom XML: paper title, full abstract/summary, all
author names (in order), the arXiv ID (numeric part of `<id>`), the year
from `<published>`, and the `term` attribute of `<arxiv:primary_category>`."*

If the `<entry>` is missing or `<title>` is `"Error"`, the ID does not exist —
report that and stop.

---

## Step 2b — Keyword search

WebFetch:

```
https://export.arxiv.org/api/query?search_query=all:<QUERY>&max_results=10&sortBy=relevance
```

URL-encode spaces as `+`. Example: `search_query=all:clifford+bianchi+groups`

Prompt: *"List the arXiv papers in this Atom XML: for each `<entry>` extract
title, authors (all names), arXiv ID, and primary category. Return as a
numbered list."*

Present the numbered list to the user. Ask which paper(s) to retrieve in full
(or proceed with all if ≤ 3 results). Then run Step 2a for each chosen ID.

---

## Step 3 — Assemble BibTeX

From the extracted metadata, generate one `@misc` entry per paper:

```bibtex
@misc{<cite-key>,
  title        = {<title>},
  author       = {<Last, First and Last, First and ...>},
  year         = {<YYYY>},
  eprint       = {<numeric-ID>},
  archivePrefix = {arXiv},
  primaryClass  = {<primary-category>},
  url          = {https://arxiv.org/abs/<numeric-ID>}
}
```

**Cite-key convention:** `<first-author-last-name><year><first-content-word-of-title>`,
all lowercase, no spaces. Example: `dupuy2024basic`.

**Author format:** invert each name to `Last, First` (or `Last, First Middle`);
separate multiple authors with ` and `.

---

## Step 4 — Return

Output all four fields for each paper:

1. **Title**
2. **Abstract** (full text)
3. **Authors** (comma-separated, natural order)
4. **BibTeX** (fenced code block)

---

## MCP enhancement (optional)

For full-paper download and reading, install `blazickjp/arxiv-mcp-server`:

```bash
uv tool install arxiv-mcp-server
```

Add to your Claude Code project settings (`.claude/settings.json`):

```json
{
  "mcpServers": {
    "arxiv-mcp-server": {
      "command": "arxiv-mcp-server"
    }
  }
}
```

Restart the session. Verify with `claude mcp list` — should show
`arxiv-mcp-server: ✓ Connected`.

When connected, the tools `mcp__arxiv-mcp-server__search_papers`,
`mcp__arxiv-mcp-server__download_paper`, and `mcp__arxiv-mcp-server__read_paper`
become available for richer workflows (local caching, semantic search, citation
graphs). The Atom API path above still works alongside it.

---

## Simple test

```
Query: arXiv ID 2407.19122
Expected title: "The Basic Theory of Clifford-Bianchi Groups for Hyperbolic n-Space"
Expected authors: non-empty list matching the arXiv API response
Expected BibTeX: non-empty @misc with eprint = {2407.19122}
```
