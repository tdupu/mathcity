# stacks-mcp

Parent: [Proof assistance](../../README.md).

Local stdio MCP server for the [Stacks Project](https://stacks.math.columbia.edu).
It retrieves informal mathematical source material; it does not check Lean proofs.

## Setup

From this server directory, create a local Python virtual environment and install
with that environment's `python -m pip install -e .`. Python >=3.10 and the
pyproject dependencies are required. Configure the active MCP host's stdio entry
with the absolute environment path to `stacks-mcp`, no arguments. Claude Code,
Codex and other hosts use their own registration/settings mechanisms. Do not
assume this local package has been published for `uvx`.

Verify initialization, tool discovery and a real content-bearing call in the
current session. A connected entry in another CLI is insufficient.

| Tool | Purpose |
|---|---|
| `get_tag(tag, include_proof)` | Statement and optional proof |
| `search_stacks(query, max_results)` | Bounded keyword/tag discovery |
| `tag_info(tag)` | Tag metadata |

For example, fetch definition `00N3`, then lemma `0BBY` with `include_proof=true`.
Inspect actual content: tags can identify chapters, and keyword previews can
carry enclosing-section labels. This server can encode retrieval/parse failures
in successful MCP payloads. Verify selected tag content and explicit zero-result
pages before making citation or empty-search claims.

See [search-stacks](../../skills/search-stacks/SKILL.md) for source-preserving
handoffs and public HTTP fallbacks, and the parent's
[Example Coverage](../../README.md#example-coverage) for executed live tests.
