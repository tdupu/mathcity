# mathcity-proof-assist

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Lean/Coq/Isabelle proof checking and arXiv bibliography for mathematics claims.

This sub-namespace (`mathcity-proof-assist.*` (ADR 0002 alias)) is the escalation target for
prose-math correctness that embeddings and reviewers cannot settle. A passing
Lean build is the strongest possible G4 (critical-review) evidence. Formulas:
`proof-check` (mechanical hurdle) + `formalize-claim` (agent → build gate).

## Using the workflow

Start with `using-mathpowers prove X` or `using-mathpowers research what is known about X`.
Requested LaTeX output routes through `using-latexpowers` within the same plan.
Both entry points use [math-workflow](../../skills/math-workflow/SKILL.md).
See the [examples and coverage](../../README-skills.md) for prerequisites and
behavioral validation; shorter aliases also resolve.

For an exposition assembled from research files, both routers use the
[selected-source synthesis sequence](../../skills/math-workflow/references/synthesis.md).
`create-exposition` gathers the chosen corpus; `rapid-prototype` sets its
audience and dependency structure; `fill-in-prototype` uses existing evidence
and resolves gaps through `using-mathpowers`; unresolved attempts surface loudly
and block dependent delivery. A single-result request may start with the exact target
and backfill prerequisites. See the [examples and coverage](../../README-skills.md#research-files-to-a-presentation).

## Skills

| Skill | Purpose |
|-------|---------|
| `install-loogle` | Install and configure a Loogle / Mathlib4 search MCP server when hosted lookup is not enough. |
| `search-arxiv` | arXiv ID or keyword → title / abstract / authors / BibTeX. Adopted upstream: [`blazickjp/arxiv-mcp-server`](https://github.com/blazickjp/arxiv-mcp-server). |
| `search-mathlib` | Lean 4 / Mathlib4 declaration search via the hosted Loogle engine. Query by name, type signature, subexpression, or conclusion pattern. Direct JSON API path (no MCP required); fail-soft on downtime. See §Loogle below. |
| `search-stacks` | Stacks Project (algebraic geometry / commutative algebra) — tag lookup and keyword search via the `mcp__stacks__*` MCP tools. |
| `search-scholar` | Semantic Scholar — paper search by keyword or title via the `mcp__scholar__*` MCP tools. |
| `using-mathpowers` | Entry point with shared planning, research, execution, review, and cleanup; see `math-workflow` |
| `using-math` | Compatibility alias for `using-mathpowers` |
| `contradiction-check` | Loud detection + refusal on claims contradicting earlier ones (tex/scratch/ledger); structured contradiction report; silent supersession prohibited |
| `create-exposition` | Selected research files to source-linked context, claims, dependencies and preserved negative findings |
| `fill-in-prototype` | Fill a presentation from evidence; research gaps and compose the proof/review/writing leaves |
| `find-proposition` | Prover-level hunt for plausible propositions -> scratch dump + conjectural ledger rows; never touches tex |
| `lean-frontier-dump` | Dump the mathematical frontier around a STUCK Lean goal — goal state, what Mathlib has nearby, the gap stated as a provable proposition, candidate and refuted routes — to a dated `ai/` package. Escalation target of `lean-formalize-prove` on bounded-retry exhaustion; for type-3 obstructions only. |

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

Shared reference: [PROVERS.md](./PROVERS.md) — harness-conditional prover backend (ADR 0005).
