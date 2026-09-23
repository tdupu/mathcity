---
name: search-arxiv
description: >
  Search arXiv by paper ID or keyword and return title, abstract, authors, and BibTeX.
  Use when asked to look up an arXiv paper, fetch metadata for a citation, check what
  a paper is about, generate BibTeX for an arXiv ID, or find papers on a topic.
---

# search-arxiv

Use the Atom API for metadata; optional
[`arxiv-mcp-server`](https://github.com/blazickjp/arxiv-mcp-server) adds full-paper
access (see §MCP enhancement).

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
author names (in order), the complete arXiv ID (strip only the URL prefix from
`<id>`), the year from `<published>`, and the `term` attribute of
`<arxiv:primary_category>`."*

Retain legacy prefixes such as `math/` and requested versions such as `v2`
in requests, metadata, eprint and URL.

For either lookup path, validate HTTP success and Atom structure. Report fetch,
parse or `Error` entries (including their summary) as failures. Only a valid,
successful empty feed establishes no result for the query.

---

## Step 2b — Keyword search

WebFetch:

```
https://export.arxiv.org/api/query?search_query=<ENCODED-QUERY>&max_results=10&sortBy=relevance
```

URL-encode the entire `all:<QUERY>` parameter value, not just spaces:
`all:C++` becomes `all%3AC%2B%2B`. Check the feed's echoed query.

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
  eprint       = {<ID>},
  archivePrefix = {arXiv},
  primaryClass  = {<primary-category>},
  url          = {https://arxiv.org/abs/<ID>}
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

Register in the project root's `.mcp.json` via:

```bash
claude mcp add --scope project --transport stdio arxiv-mcp-server -- arxiv-mcp-server
```

Restart; check `claude mcp list` for connection status and discover session tools.

When connected, the tools `mcp__arxiv-mcp-server__search_papers`,
`mcp__arxiv-mcp-server__download_paper`, and `mcp__arxiv-mcp-server__read_paper`
support download/read and local caching. Citation graphs use `citation_graph`;
`semantic_search` additionally requires the optional `arxiv-mcp-server[pro]`
install. The Atom path remains available.

---

## Simple test

```
Query: arXiv ID 2407.19122
Expected title: "The Basic Theory of Clifford-Bianchi Groups for Hyperbolic n-Space"
Expected authors: non-empty list matching the arXiv API response
Expected BibTeX: @misc with eprint containing 2407.19122; retain requested version
```
