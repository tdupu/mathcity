---
name: search-mathlib
description: Use when looking up Lean or Mathlib declarations by mathematical description, name, type, subexpression or conclusion, or finding an identifier's defining module.
---

# Find Mathlib declarations

Input: mathematical query, optional pinned workspace, and channels already tried.
Output: candidate names, types, imports, sources and coverage; distinguish checked
applications from search leads and unavailable services from empty results.

## Select a search channel

Discover actual tools/schemas in the active host. With
[lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp), use
`lean_leansearch(query,num_results)` for natural-language discovery and
`lean_loogle(query,num_results)` for names or formal patterns. Existing mathlas
`search_formal_math` is another option; inspect its schema. A package installed
on disk or `claude mcp list` in another host does not prove session availability.
Requested setup routes to `install-loogle`; ordinary lookup does not install.

Without MCP, query [Loogle](https://loogle.lean-lang.org) directly:

```sh
curl -fsS --get --data-urlencode 'q=add_comm' https://loogle.lean-lang.org/json
```

Inspect JSON `hits` with name/module/type/doc, or the explicit query `error`.
`add_comm` should return a declaration of commutativity, but its module/type may
change with the index. Never hardcode a returned declaration's applicability.

The tested [LeanSearch](https://leansearch.net) fallback is POST `/search` with
JSON `{"query":["addition is commutative"],"num_results":"5"}`. Validate the
actual nested result lists. HTTP, network, payload or schema failure is an
unavailable channel, not “no lemma exists.” Report query errors separately.

| Loogle mode | Example |
|---|---|
| Mention a constant | `Real.sin` |
| Name substring | `"add_comm"` |
| Subexpression | `_ * (_ ^ _)` |
| Conclusion | `⊢ ?a + ?b = ?b + ?a` |

Combine filters with commas; quote query strings and URL-encode them. Inspect
neighboring and more general formulations rather than assuming one name.

## Check and return

Report relevant full names, types, defining modules and direct documentation
links. Remote indices can differ from the project's Mathlib pin. For requested
formal reuse, invoke installed `lean-search` with the candidate receipts and
already-searched/unavailable channels: local `#check @name` and a compiled
application must establish applicability. It must not retry this leaf as an
unbounded fallback. Without Lean, label results as unverified candidates.

For broader searches when hosted channels fail, use local source search and
the pinned CLI; a specifically MCP/Loogle-only request reports its blocked
capability. Preserve exact queries, coverage, outages and hypothesis differences.
Neither failed search nor automation proves absence or novelty.

A Stacks prerequisite routes through `search-stacks`, retaining the actual tag,
statement and assumptions as informal evidence. Requested formalization returns
to `using-leanpowers` under the existing coordinator; lookup alone does not prove
the mathematical source claim.
