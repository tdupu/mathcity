# mathcity-proof-assist

Lean/Coq/Isabelle proof checking and arXiv bibliography for mathematics claims.

This sub-namespace (`mathcity-proof-assist.*` (ADR 0002 alias)) is the escalation target for
prose-math correctness that embeddings and reviewers cannot settle. A passing
Lean build is the strongest possible G4 (critical-review) evidence. Formulas:
`proof-check` (mechanical hurdle) + `formalize-claim` (agent → build gate).

## Skills

| Skill | Purpose |
|-------|---------|
| `search-arxiv` | arXiv ID or keyword → title / abstract / authors / BibTeX. Adopted upstream: [`blazickjp/arxiv-mcp-server`](https://github.com/blazickjp/arxiv-mcp-server). |
| `search-mathlib` | Lean 4 / Mathlib4 declaration search via the hosted Loogle engine. Query by name, type signature, subexpression, or conclusion pattern. Direct JSON API path (no MCP required); fail-soft on downtime. See §Loogle below. |
| `search-stacks` | Stacks Project (algebraic geometry / commutative algebra) — tag lookup and keyword search via the `mcp__stacks__*` MCP tools. |
| `search-scholar` | Semantic Scholar — paper search by keyword or title via the `mcp__scholar__*` MCP tools. |

## Loogle

[Loogle](https://loogle.lean-lang.org) is the canonical search engine for Lean 4 / Mathlib4, hosted by the Lean FRO. It indexes the full Mathlib4 library.

The `search-mathlib` skill uses Loogle as its primary backend via the hosted JSON API:

```
https://loogle.lean-lang.org/json?q=<URL-encoded query>
```

**Three query modes** (combine with commas for AND-filter):

| Mode | Example | Effect |
|------|---------|--------|
| By name / constant | `add_comm` | All lemmas mentioning `add_comm` |
| By name substring | `"add_comm"` | All lemmas with `"add_comm"` in their name |
| By conclusion | `\|- ?a + ?b = ?b + ?a` | Lemmas whose conclusion matches the pattern |

The API returns `{count, hits: [{name, module, type, doc}]}` on success or `{error, suggestions}` on no match. The skill fails soft (P1.14) on API downtime or format drift.
