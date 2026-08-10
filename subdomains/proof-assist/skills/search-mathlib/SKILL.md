---
name: search-mathlib
description: Search Lean 4 Mathlib4 declarations via the Loogle search engine (https://loogle.lean-lang.org). Use this skill whenever the user wants to look up a Lean lemma, theorem, definition, or typeclass; search by name, type signature, or subexpression; verify that a Lean statement exists in Mathlib; or find the module that defines a given identifier. Trigger on phrases like "find in Mathlib", "search Mathlib for", "look up Lean lemma", "what does Loogle say about", "search for commutativity of addition", "is there a Lean theorem for X", or any request to find Lean 4 / Mathlib declarations.
---

# Mathlib4 Search via Loogle

Loogle is the canonical search engine for Lean 4 / Mathlib4, hosted at https://loogle.lean-lang.org by the Lean FRO. It indexes the full Mathlib4 library and supports four complementary query styles.

Existing MCP servers for Loogle/Mathlib (adopt/cite if configured):
- **mathlas** (`search_formal_math` tool) — wraps Loogle + LeanSearch with a 7-day cache. Install: `claude mcp add mathlas -- uvx mathlas-mcp`. Source: https://github.com/Archerkattri/mathlas
- **lean-mathlib-docs-mcp** — local docs search. Source: https://github.com/CriticalLine/lean-mathlib-docs-mcp
- **lean-lsp-mcp** — full LSP-based server with Loogle integration. Source: https://github.com/oOo0oOo/lean-lsp-mcp

## Primary path: mathlas MCP server

If mathlas is configured (`claude mcp list` shows `mathlas: ✓ Connected`), call `search_formal_math` with the query. Its `search_formal_math` tool proxies Loogle + LeanSearch and returns declaration names and types.

## Direct API path (no MCP required)

Query the Loogle JSON API directly with WebFetch or Bash:

```bash
curl -s "https://loogle.lean-lang.org/json?q=add_comm"
```

Or in a skill using WebFetch:
- URL: `https://loogle.lean-lang.org/json?q=<URL-encoded query>`
- Returns JSON: `{count, header, hits: [{name, module, type, doc}], heartbeats}`
- On no match: `{error: "...", suggestions: [...], heartbeats}`

**PASS test**: `add_comm` → `count > 0`, first hit `name: "add_comm"`, `type: "{G : Type u_1} [AddCommMagma G] (a b : G) : a + b = b + a"` (non-empty Lean statement).
**FAIL test**: nonsense query → `error` field present, empty or absent `hits`.

## Fail-soft (P1.14)

If the WebFetch call fails (non-200 HTTP status, connection refused, or a response body that is not valid JSON or is missing both `hits` and `error` fields), **stop and report**:

> I'm sorry, I can't do that — the Loogle API at loogle.lean-lang.org is not responding as expected (`<HTTP status or description>`).
> Wait a few minutes and retry, or check https://loogle.lean-lang.org in a browser to verify the service is up.
> (Loogle is the hosted search engine for Lean 4 / Mathlib4 declarations; without it, Mathlib lemma lookup is unavailable.)

**API drift**: if the JSON shape changes (e.g., `hits` is renamed or the top-level keys differ from `{count, header, hits, error, heartbeats}`), log the actual response keys and emit the same error with `(API format drift detected)` rather than attempting to parse unknown structure.

Do NOT silently return empty results when the real cause is a connectivity failure.

## Loogle query syntax

Loogle supports four query modes; combine them with commas for AND-filter:

| Mode | Syntax | Example | Effect |
|------|--------|---------|--------|
| By constant | bare identifier | `Real.sin` | All lemmas mentioning `Real.sin` |
| By name substring | `"quoted"` | `"differ"` | All lemmas with `"differ"` in their name |
| By subexpression | `_ op _` | `_ * (_ ^ _)` | Lemmas containing a product of a power |
| By conclusion | `\|- pattern` | `\|- tsum _ = _ * tsum _` | Lemmas whose conclusion matches |

Metavariables (`?a`, `?b`) match any subexpression. Hypothesis order in the conclusion filter is flexible.

**Combined example**: `Real.sin, "two", \|- _ < _ → _` — finds lemmas mentioning `Real.sin`, with `"two"` in their name, and a hypothesis `_ < _`.

**Type filter examples**:
- `⊢ (_ : Type _)` — definitions that provide data
- `⊢ (_ : Prop)` — theorems and proofs

## Response format

Each `hit` in the JSON array contains:
- `name` — fully-qualified Lean identifier (e.g. `Mathlib.Algebra.Group.Defs.add_comm`)
- `module` — the Mathlib module that defines it (e.g. `Mathlib.Algebra.Group.Defs`)
- `type` — the full Lean 4 type signature
- `doc` — docstring or `null`

Documentation link pattern: `https://leanprover-community.github.io/mathlib4_docs/<Module/Path>.html#<name>`

## Standard workflow

1. **Identify query style** — name lookup (`add_comm`), type search (`_ + _ = _ + _`), or conclusion search (`|- a + b = b + a`)
2. **Call Loogle** — via mathlas `search_formal_math` if available, else `WebFetch` the JSON API
3. **Report hits** — show `name`, `type`, and documentation URL for each relevant result
4. **Escalate to proof-assist** — if the goal is formal verification rather than search, hand off to the `proof-assist` formula

## Common queries

| Goal | Query |
|------|-------|
| Commutativity of addition | `add_comm` |
| All `add_comm`-style lemmas | `"add_comm"` |
| Type-class instances for rings | `[Ring ?α]` |
| Lemma about tsum | `tsum` |
| Lemma concluding `a + b = b + a` | `\|- ?a + ?b = ?b + ?a` |
| List.map signature | `(?a -> ?b) -> List ?a -> List ?b` |
