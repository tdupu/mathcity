---
name: search-stacks
description: Use when retrieving or verifying a Stacks Project tag, searching its definitions or results, or obtaining a tagged statement and proof in algebraic geometry or commutative algebra.
---

# Retrieve Stacks source evidence

Input: tag or keyword query and the caller's mathematical scope.
Output: verified tag URL, statement, hypotheses, available proof and retrieval
snapshot, or a precise retrieval limitation. Preserve the active coordinator.

Discover current-host tools and schemas; server prefixes vary. The local Stacks
MCP exposes:

| Tool | Purpose |
|---|---|
| `get_tag(tag, include_proof=false)` | Tagged statement and optional proof |
| `search_stacks(query, max_results=20)` | Bounded keyword search |
| `tag_info(tag)` | Type, chapter/section and source URL |

Fetch known tags directly. Otherwise search, then fetch selected tags rather
than citing previews. Use bounded `max_results`; quoted phrases such as
`"flat module"` and wildcard `ideal*` are supported by the site's search.
`00N3` is a definition; `0BBY` is a lemma with proof. Tags can also identify
chapters: requesting a proof for `01YT` does not produce a theorem proof.

Inspect content as well as MCP success. Preview labels/counts can be incomplete
or refer to enclosing sections. The current server can encode network errors
as successful tool payloads, and a failed HTML parse can appear as zero results.
Confirm an explicit zero-result search page through direct HTTP before claiming
an empty search; otherwise report retrieval/parse uncertainty.

## Setup and fallback

For requested setup, locate the canonical server beside this skill at
`../../mcp/stacks` and read its README. Install it into a local virtual environment
and register the absolute `stacks-mcp` executable as a stdio command in the active
host. Do not assume a published `uvx stacks-mcp` package or require Claude CLI
for another host. Smoke-test tool discovery and an actual tagged statement/proof;
registration alone does not establish callability in this session.

Without MCP, fetch public HTML directly, URL-encoding query parameters:

```text
https://stacks.math.columbia.edu/data/tag/00N3/content/statement
https://stacks.math.columbia.edu/data/tag/0BBY/content/full
https://stacks.math.columbia.edu/search?query=%22flat%20module%22
```

Validate HTTP status and expected statement/proof/search content. Preserve
LaTeX mathematics while extracting HTML; don't invent unavailable raw-LaTeX or
metadata endpoints. Missing MCP/source blocks only that setup path; public
retrieval remains available. Report HTTP/network/parse failures distinctly from
a successful empty search or an absent proof.

## Return to mathematics or formalization

Verify the selected tag's actual type/title, assumptions, conclusion and proof.
Record `https://stacks.math.columbia.edu/tag/TAG`, retrieval date and source
snapshot; follow relevant dependencies with precise locators.

A published Stacks proof is informal source evidence, not a Lean certificate.
Mathpowers consumes it for research/proof context. Requested formalization goes
to `using-leanpowers`, carrying the statement, proof and source receipts through
claim extraction, alignment and `lean-search`. A Mathlib match must compile
under the target pin; unresolved prerequisites remain obligations. Only current
verification plus source-fidelity review can support FORMALIZED status.
