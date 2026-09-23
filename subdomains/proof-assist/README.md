# mathcity-proof-assist

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Lean/Coq/Isabelle proof checking and arXiv bibliography for mathematics claims.

This sub-namespace (`mathcity-proof-assist.*` (ADR 0002 alias)) is the escalation target for
prose-math correctness that embeddings and reviewers cannot settle. Lean compilation checks the formal statement; separate source-fidelity review
is required before claiming it proves the original mathematical claim. Formulas:
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
| `install-loogle` | Host-neutral LeanSearch/Loogle MCP setup and actual tool smoke tests. |
| `search-arxiv` | arXiv ID or keyword → title / abstract / authors / BibTeX. Adopted upstream: [`blazickjp/arxiv-mcp-server`](https://github.com/blazickjp/arxiv-mcp-server). |
| `search-mathlib` | LeanSearch semantic and Loogle name/type search through MCP or direct HTTP; local pinned applicability checks via installed `lean-search`. |
| `search-stacks` | Stacks tagged statements/proofs and keyword lookup through discovered MCP tools or direct HTTP. |
| `search-scholar` | Semantic Scholar — paper search by keyword or title via the `mcp__scholar__*` MCP tools. |
| `using-mathpowers` | Entry point with shared planning, research, execution, review, and cleanup; see `math-workflow` |
| `using-math` | Compatibility alias for `using-mathpowers` |
| `contradiction-check` | Loud detection + refusal on claims contradicting earlier ones (tex/scratch/ledger); structured contradiction report; silent supersession prohibited |
| `create-exposition` | Selected research files to source-linked context, claims, dependencies and preserved negative findings |
| `fill-in-prototype` | Fill a presentation from evidence; research gaps and compose the proof/review/writing leaves |
| `find-proposition` | Prover-level hunt for plausible propositions -> scratch dump + conjectural ledger rows; never touches tex |

## Search and formalization

`using-mathpowers` dispatches natural-language and typed Mathlib queries through
[search-mathlib](skills/search-mathlib/SKILL.md), setup requests through
[install-loogle](skills/install-loogle/SKILL.md), and Stacks references through
[search-stacks](skills/search-stacks/SKILL.md). Discover tools in the active host;
registration in a different CLI does not establish availability in this session.

For example, ask `using-mathpowers: find a Mathlib lemma for commutativity of
addition`, or `using-mathpowers: retrieve Stacks tag 0BBY with its proof`.
LeanSearch supplies semantic candidates; Loogle handles names and type patterns.
Fetch selected Stacks tags to verify their exact statements and assumptions.
Preview labels and result counts are discovery aids, not authoritative citations.

For requested formalization, invoke installed `using-leanpowers` under the same
plan and pass source receipts into claim extraction, alignment and `lean-search`.
Compile candidate applications in the target project: online Mathlib indices may
use different names or modules. Stacks prose is informal evidence, never a Lean
certificate. Missing optional MCP tools have direct HTTP and local CLI fallbacks.

The tested Lean MCP 0.30.0 requires Lean >=4.24 for local LSP. Older projects keep
their pins and use CLI checks. No project upgrade or global MCP registration is
implied by ordinary search. Setup details belong to the linked skills and
[Stacks server guide](mcp/stacks/README.md).

### Example Coverage

Development evidence is deliberately untracked, per the user's test-scope
instruction. Paths below are relative to the agent-skills checkout used for the
run; a clean checkout provides the skills, not these saved local transcripts.

| Example | Runner | Prerequisites | Command | Test path | Status | Issue |
|---|---|---|---|---|---|---|
| Mathlib query | Agent/integration | Lean MCP or public HTTP; Lean for applicability | `using-mathpowers: find add_comm and check it in this project` | `ai/leanpowers-2026-09-20/mcp-handoff/` | Live search and pinned application passed | N/A |
| Stacks lemma and proof | Agent/integration | Stacks MCP or public HTTP | `using-mathpowers: retrieve tag 0BBY with proof` | `ai/leanpowers-2026-09-20/mcp-integration/` | Live tagged proof retrieval passed; no formalization claim | N/A |
| Local goal/diagnostics | Integration | Compatible Lean MCP, Lean 4.24 fixture | Discovered `lean_goal` and `lean_diagnostic_messages` tools | `ai/leanpowers-2026-09-20/mcp-integration/` | Good goal and intentional-error checks passed | N/A |

Shared reference: [PROVERS.md](./PROVERS.md) — harness-conditional prover backend
(ADR 0005).
