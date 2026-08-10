# stacks-mcp

MCP server wrapping the [Stacks Project](https://stacks.math.columbia.edu) API — algebraic geometry and commutative algebra reference.

## Install

```bash
pip install -e .
```

## Configure

```bash
claude mcp add stacks -- stacks-mcp
```

Or via `uvx` once published:

```bash
claude mcp add stacks -- uvx stacks-mcp
```

## Tools

| Tool | Description |
|------|-------------|
| `get_tag(tag, include_proof)` | Statement (and optional proof) for a tag |
| `search_stacks(query, max_results)` | Keyword search, returns tags with previews |
| `tag_info(tag)` | Metadata: type, chapter, section, book\_id |

## Example

```
get_tag("00N3")          # Cohen-Macaulay definition
search_stacks("flat*")   # all tags mentioning "flat..." 
```
