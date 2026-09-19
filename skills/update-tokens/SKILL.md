---
name: update-tokens
description: Sole write path for a repository's master tokens.md — the priced AI cost record. Prepends one block per task and agent with token counts by class (input, output, cache write 5m/1h, cache read), the model, a per-row rate block with its date basis, computed USD cost, wall-clock, and a measured/estimated/mixed source label. Implements AI-POLICY.md AI16; the policy governs, this is the mechanism. Use on "update tokens", "price this task", "what did that cost", or when a skill finishes an AI task whose spend needs recording. Also writes per-folder working ledgers and consolidates them upward. NOT for provenance, AI-results, or literature searches (update-ai-usage, which mints the task ID this skill prices against).
---

# update-tokens

What each AI task cost, readable without opening another file. Sole writer
(AI15). AI16 governs; this file is the mechanism and does not restate it.

**Contract:** the repo's `AI-POLICY.md`, resolved repo-local-first per
`subdomains/repo-docs/RESOLUTION.md`. On a miss, never treat the pack template
as authority and never edit anything under `mathcity/`: report that the repo
needs `new-repo-ai-policy`. A repo copy that tightened AI16 wins.

## Scope of the figure

This ledger prices **token charges**. That is what AI16's `rate x tokens`
asks for, and it is what telemetry supports. Charges outside that model are
**named, not silently dropped** — record them in the row's Notes with their
own units when they occurred, and say in the grand total that the total is
token-charges-only:

- per-call charges (web search is billed per thousand searches — AI5's
  mandated literature search generates these routinely), code-execution or
  container time, session runtime;
- rate modifiers not folded into the per-million rates: batch discounts,
  priority/fast tiers, region multipliers.

A total that quietly omits these while claiming to be "the cost" is the
invented-figure failure AI16 exists to prevent. Naming the omission is
compliant; hiding it is not.

## Entry points

| Invoked | Do |
| --- | --- |
| by a human | resolve the root, write or create the master `tokens.md` |
| by a caller holding a working ledger | write the caller's ledger in this schema, then consolidate upward |

Root: `git rev-parse --show-toplevel`. Outside a repo — a prompt-package or
other artifact tree — the work root is the caller's top-level package
directory, stated in the file; never invent a repo. A caller's working ledger
is not a competing ledger; only an unconsolidated second ledger at the
repository root is a finding.

## Task ID

Rows key on the task ID `update-ai-usage` mints
(`<ISO-date>T<HH:MM>-<skill>-<slug>`). When a caller invokes this skill alone
— the common case in prompt-package pipelines — mint a **provisional** ID in
the same format, mark the row `provenance: absent`, and report that
`update-ai-usage` has not run for this task. Never leave it blank: an unkeyed row
cannot be reconciled or de-duplicated.

**Clearing a provisional ID.** When `update-ai-usage` later mints the real ID
for the same task, it reports it; this skill — the only writer of `tokens.md`
— then rewrites the provisional ID to the real one and removes the
`provenance: absent` mark. That is the second permitted in-place edit, and it
is recorded in Notes. Without it the priced record asserts forever that
provenance is missing for a task that has an entry.

## Row schema

One row per **task and agent** — sub-rows for stages or forks indent under
their task row and sum to it. `frontier-dump` and `fp-finder-latex` both require
agent identifiers on the priced record.

| Field | Content |
| --- | --- |
| Task ID | the `update-ai-usage` ID, or a provisional one |
| Agent / call ID | which agent spent it, whenever the harness exposes one |
| Date | ISO 8601 with offset |
| Model | model identifier the tokens were spent on (AI1) |
| Tokens | one line per class: input, output, cache write 5m, cache write 1h, cache read — cache is **never** folded into plain input |
| Source | `measured`, `estimated (<method>)`, or `mixed` with a per-figure breakdown |
| Rates | the full rate block applied, one line per token class, so the row recomputes independently |
| Rate basis | the provider's published **effective** date; absent one, the date checked, labelled `checked` — never label a check date as an effective date |
| Cost (USD) | `sum over classes (tokens_class x rate_class) / 1e6` — computed, never recalled, token charges only |
| Duration | wall-clock span. **Never sum overlapping intervals** — concurrent forks report the union's span plus each fork's own |
| Bound | when a figure rests on an assumed split: the true minimum (all tokens at the cheapest class that could account for them) and maximum |
| Notes | non-token charges and rate modifiers, with units; source paths on consolidation |

Because the fields are multi-line, entries are **blocks, not table rows** — a
thirteen-column markdown table does not render, and two agents appending to
one would produce incompatible ledgers. Worked example:

```markdown
### 2026-09-19T14:32-10:00__frontier-dump__jacobi-smoothness
| field | value |
| --- | --- |
| agent | astra-7f3 (primary) |
| model | gpt-6-astra |
| tokens | in 412,900 · out 38,110 · cache-read 1,204,000 |
| source | measured (harness telemetry) |
| rates | in 1.25/M · out 10.00/M · cache-read 0.125/M |
| rate basis | checked 2026-09-19 (provider publishes no effective date) |
| cost (USD) | 1.05 — token charges only |
| duration | 00:41:08 |
| notes | 3 web searches, billed per-call, not in the figure above |
```

Prepend, newest first, **below the file header and the grand total** — the
total sits directly under the header so it is the first thing read, and is
recomputed on every write. It states which rows are measured, which estimated,
and that it covers token charges only. Superseded rows are excluded.

## Pricing

Look the rates up; never use memorized figures. Prefer the provider's
published pricing page and record its effective date when it publishes one.
The `claude-api` skill is a **versioned fallback**, not a live table — it
ships inside the CLI binary, so its figures are as-of that release; record the
CLI version when you use it. It prices no non-Anthropic model.

Cache multipliers differ by class **and by model** — resolve them per model
rather than assuming a house default, and record the multiple you used in the
rate block. Where a harness reports a single aggregate token scalar with no
class breakdown (a subagent token total, for instance), that is an unsplit
aggregate: state the split you assumed, give the Bound, and label the row
`estimated`. Do not refuse, and do not silently treat the aggregate as plain
input.

Multi-**model** tasks are priced per model and summed, never averaged into a
single cross-model rate. That is a different question from an input/output
**split assumption** on an unsplit aggregate, which is permitted when stated
and bounded. Callers that speak of a "blended estimate" mean the split
assumption; this rule forbids only the cross-model average.

## Superseding a row

An estimate is replaced **in place** when real telemetry arrives — annotate
`was: estimated (<method>) <figure>` and recompute the total. That is the only
in-place edit, and it extends to a working ledger the caller already wrote. A
**rate** change never touches an old row: append a correction row, mark the
original `superseded`, exclude it from the total.

## Consolidating upward

1. Discover working ledgers from the resolved root `$ROOT`:
   `find "$ROOT" -type f -name tokens.md ! -path "$ROOT/tokens.md" \
    -not -path '*/.git/*' -not -path '*/node_modules/*'`.
2. Skip any bearing `<!-- consolidated: <task-id> -->`.
3. One master row per task ID; stages and forks stay as sub-rows.
4. Record source paths in the row's Notes, then stamp the source with the
   marker. Leave its content unedited; never delete it (AI15).

## Gates

Refuse, and report what is missing, when:

- The model is unknown (AI1) — an unattributed count cannot be priced.
- Tokens are unknown and no labelled estimate method applies.
- Cache tokens are present with no cache rate resolved.
- A rate has no date basis of either kind.

Never invent a count, a rate, or a cost.

## Report back

Ledger paths, the task ID priced (flagging a provisional one), the rate block
with its basis and source, the grand total in tokens and USD with its
token-charges-only scope, any non-token charge recorded in Notes, any estimate
awaiting replacement, and any ledger consolidated.
