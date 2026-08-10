---
name: search-stacks
description: Query the Stacks Project (stacks.math.columbia.edu) for theorems, lemmas, definitions, and proofs in algebraic geometry and commutative algebra. Use this skill whenever the user asks about a Stacks tag, wants to look up a statement in the Stacks Project, search for results by keyword, verify a reference, or retrieve LaTeX source for a known result. Trigger on phrases like "look up in Stacks", "what does the Stacks project say about", "find the Stacks tag for", "fetch tag 00XY", "search Stacks for Cohen-Macaulay", or any request to query algebraic geometry definitions/lemmas/theorems from the Stacks Project.
---

# Stacks Project Search Skill

The Stacks Project MCP server gives tag lookup and keyword search access to
[stacks.math.columbia.edu](https://stacks.math.columbia.edu).
Tools are available as `mcp__stacks__*` once configured.

## Existing MCP servers (adopt/cite if available)

No established third-party Stacks MCP server is known as of 2026-07.
This skill ships its own server; see **Setup** below.

## Setup

Install and configure the server once per machine:

```bash
pip install -e <mathcity-pack-root>/subdomains/proof-assist/mcp/stacks
claude mcp add stacks -- stacks-mcp
```

Verify with `claude mcp list` — should show `stacks: ✓ Connected`.

If the tools are not available in this session, say:

> I'm sorry, I can't do that — the stacks MCP server is not connected.
> Configure it with: `pip install -e .../mcp/stacks && claude mcp add stacks -- stacks-mcp`
> then restart your Claude Code session.

## Available tools

| Tool | Purpose |
|------|---------|
| `mcp__stacks__get_tag(tag, include_proof)` | Statement (+ optional proof) for a 4-char tag |
| `mcp__stacks__search_stacks(query, max_results)` | Keyword search; returns tag list with LaTeX previews |
| `mcp__stacks__tag_info(tag)` | Metadata: type, book\_id, chapter, section |

## Standard workflow

1. **Known tag** → `get_tag("XXXX")` directly.
2. **Keyword search** → `search_stacks("keyword*")` to find tags, then `get_tag` on the relevant one.
3. **Location context** → `tag_info("XXXX")` to get chapter/section placement.

## Search syntax

The search engine uses SQLite FTS3:
- `ideal*` matches "ideal", "ideals", "idealization", …
- `"quasi-compact"` (quoted) prevents the hyphen being read as NOT.
- Default returns up to 20 results; pass `max_results=N` for more.

## LaTeX output format

Statements are returned as LaTeX-rich text:
- Inline math: `$...$`
- Display math: `\[...\]` or `\begin{equation}...\end{equation}`
- Theorem environments preserved as plain text with the environment name as prefix.

## Example queries

**Fetch a known tag:**
```python
get_tag("00N3")          # → Definition 10.103.1 (Cohen-Macaulay modules)
get_tag("00XY")          # → Lemma 7.22.2 (morphisms of sites)
get_tag("01YT", include_proof=True)  # includes proof
```

**Keyword search:**
```python
search_stacks("Cohen-Macaulay")          # 306 results
search_stacks('"flat module"', 10)       # exact phrase
search_stacks("etale*")                  # wildcard
```

**Tag metadata:**
```python
tag_info("00N3")
# tag: 00N3
# type: definition
# book_id: 10.103.1
# chapter: Chapter 10: Commutative Algebra
# section: Section 10.103: Cohen-Macaulay modules
# url: https://stacks.math.columbia.edu/tag/00N3
```

## Direct API fallback (no MCP required)

If the MCP server is unavailable, the Stacks website has HTML endpoints:

```bash
# Statement HTML (contains LaTeX as $...$)
curl "https://stacks.math.columbia.edu/data/tag/00N3/content/statement"

# Full statement + proof HTML
curl "https://stacks.math.columbia.edu/data/tag/00N3/content/full"

# Keyword search (returns HTML tree with previews)
curl "https://stacks.math.columbia.edu/search?query=Cohen-Macaulay"
```

Note: raw LaTeX and JSON metadata endpoints (`/data/tag/TAG/meta`, `.../raw`) are
not currently served; use the HTML endpoints and strip tags to recover LaTeX.
