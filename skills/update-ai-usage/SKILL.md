---
name: update-ai-usage
description: Sole write path for a repository's master ai-usage.md — the AI provenance record. Appends one dated, identified entry per task: per-agent model and harness from caller through every descendant, skill chain, inputs and their human/AI provenance, work performed, AI-results with derivation accounts and literature-search outcomes, reference-verification marks, negative results, review and integration status, scope limits. Implements AI-POLICY.md's record rules; does not restate them. Use on "update ai-usage", "record the AI usage for this task", "append to ai-usage.md", or when a skill that ran an AI task needs its provenance recorded. Also writes per-folder working records and consolidates them upward. NOT for token counts, rates, or cost (update-tokens), NOT for manuscript disclosure prose (write-materials-and-methods), and NOT for session run-logs or memories (mayor-math-handoff, remember-this).
---

# update-ai-usage

The provenance record the manuscript's disclosure is later drafted from, and
the evidence `latex-ai-statement` audits it against. Sole writer (AI15).

**Contract:** the repo's `AI-POLICY.md`. Read it before writing and follow its
record rules; do not restate or widen them here. Resolve it repo-local-first
per `subdomains/repo-docs/RESOLUTION.md`: on a miss, do **not** fall back to
the pack template and do **not** edit anything under `mathcity/` — report that
the repo needs `new-repo-ai-policy`, record the entry against the template's
rules, and say plainly that no instantiated policy governed the write.

## NOT for

- Token counts, rates, cost → `update-tokens` (paired; run both per task)
- Manuscript prose → `write-materials-and-methods`
- Auditing a `.tex` disclosure → `latex-ai-statement`
- Running the literature search → `search-arxiv`, `search-scholar`,
  `track-down-reference`

## Two record tiers

| Tier | Location | Who writes it |
| --- | --- | --- |
| Working record | the artifact folder (dump, correction root, prompt package) | this skill, same schema |
| Master record | repository root (`git rev-parse --show-toplevel`). Outside a repo — an artifact tree such as a prompt-package directory — the work root is the caller's top-level package directory, and the entry says so; never invent a repo | this skill, by consolidation |

A caller may name a different root for its working record — `triage-referee-report`
uses the correction/revision root for a whole review. Honour it; that is a
working record, not a competing ledger. **Only an unconsolidated second
ledger at the repository root is a finding**, reported with its path.
Consolidated sources stay on disk, unedited, as evidence (AI15). A caller
that asks for the working record to be **deleted** after consolidation is
refused on the AI15 floor: report the conflict and name the caller. Removing
a duplicate *root* ledger is a different act and is allowed.

## Entry format

Prepend — newest first. One entry, one heading, stable ID:

```markdown
## 2026-09-19T14:32-10:00 — frontier-dump/jacobi-smoothness
[id: 2026-09-19T14:32-10:00__frontier-dump__jacobi-smoothness]
**Consolidated from:** `scratch/2026-09-19-frontier-jacobi/ai-usage.md`
**Prompt:** <what the human asked, plus mid-task direction>
**Agents:**

| Role | Agent ID | Requested model | Observed model | Harness | Effort |
| --- | --- | --- | --- | --- | --- |
| caller | — | claude-opus-5 | claude-opus-5 | Claude Code | high |
| primary | frontier-7f3 | gpt-6-astra (best available at run time) | gpt-6-astra | Frontier API | — |
| descendant | frontier-7f3.1 | gpt-6-astra | not recorded | Frontier API | — |

**Skill chain:** frontier-dump → search-arxiv
**Inputs:** `notes.tex` §3 (human); `2026-09-12` dump conjecture list (AI)
**Work performed:** …
**Sources & computations:** … (AI13 governs the wording)
**AI-results (AI4 — every result names what produced it):**

| # | Result | Produced by (model / harness / skill) | Derivation account | Literature search | Refs verified |
| --- | --- | --- | --- | --- | --- |
| 1 | counterexample to Conj. 3.2 | gpt-6-astra / Frontier API / frontier-dump | … | 1 hit, [Ser73, Thm 4.1], compared: … | Ser73 verified (AI11) |
| 2 | reformulation of Def. 2.1 | claude-opus-5 / Claude Code / — | … | searched, no hits | — |
| 3 | drafted §2.3 prose | claude-opus-5 / Claude Code / — | … | pending — `<owner>` | — |
**Retention (AI15):** where this entry's transcripts and raw telemetry live,
when it differs from the policy header's default — the evidence beneath the
accounts above
**Negative results (AI14):** refutations, counterexamples, failed
expectations — recorded even when the session produced nothing else
**Review:** agent review: <what>. Human verification: <what, or none yet>.
**Integration:** <where it landed in the manuscript, or not yet integrated>
**Scope limits / withheld:** …
```

**The ID is minted here (AI20)** — `<ISO-8601-datetime-with-offset>__<skill>__<slug>`,
double underscore separating the three fields because `-` occurs inside all
of them. The offset is required, so agents in different zones cannot mint
colliding keys. `<skill>` is the full skill name, `<slug>` unique in the repo.
Example: `2026-09-19T14:32-10:00__frontier-dump__jacobi-smoothness`. It is the join key `update-tokens`
prices against; hand it to `update-tokens` for the same task. When a caller
invokes `update-tokens` alone, that skill mints a provisional ID and records
that no provenance entry exists — this skill adopts it on the next write
rather than minting a second one. **Idempotency:** an existing ID is amended
in place and the amendment is stated; a genuinely distinct run gets a new ID.
Never overwrite one run's evidence with another's.

Unknown fields say `not recorded`, never a guess. A search not yet run is recorded in the
**Literature search** column as `pending — <owner>`: a recordable state, not
a blocked write.

## Capture at write time

Version facts are unrecoverable later. When a task uses a tool not yet in the policy's
declared-tools table, resolve the facts **now** — version or model id, the
repo commit or tag for a skill, the `.bib` key, the access date — and record
them in this entry. Then **report the missing row and route to
`new-repo-ai-policy`**: `AI-POLICY.md` is its sole write path and a row added
here would bypass the human gate. Capture the facts, propose the row, never
edit the contract.

## Consolidating upward

**An index is not a source (AI20).** A roll-up index over event records — the
established name in this estate is `usage.md` — is a link list pointing at the
records it covers. It is never an event, and consolidating one counts every
record it indexes a second time. Discover `ai-usage.md` only; where an index
exists, leave it untouched and report it as an index.

Going forward, **an index declares itself on its first line** — for example
"This is a root index, not a usage event." Classify every candidate three
ways, and never guess:

| What you find | Treat as |
| --- | --- |
| A first-line index declaration | index — never consolidate |
| No declaration and no index signal | record — consolidate normally |
| No declaration but an index signal — an H1 naming it an index, or links to a sibling `ai-usage.md` / `tokens.md` | **ambiguous** — report the path, do not consolidate, ask for a human disposition |

The asymmetry is deliberate. Guessing "record" on an index double-counts
silently and every individual row still reads as correct; guessing "index" on
a record under-counts, which surfaces later as a task with no entry under AI4
and AI5. Where the evidence does not decide, fail toward the visible error.

1. Discover working records from the resolved root `$ROOT`:
   `find "$ROOT" -type f -name ai-usage.md ! -path "$ROOT/ai-usage.md" \
    -not -path '*/.git/*' -not -path '*/node_modules/*'`.
2. Skip any already bearing `<!-- consolidated: <task-id> -->`.
3. **Skip mirrors.** One run spanning several repositories leaves the same
   task IDs in each one's records. Task IDs are globally unique, so a source
   whose IDs already appear in this ledger is a mirror: report it with its
   path and skip it. Never sum mirrors — a three-repository run summed three
   times looks exactly like a correct ledger, and no individual number appears
   wrong.
4. One master entry per task ID, not per file; a record covering several tasks
   yields several entries.
5. Cite every source path in `Consolidated from:`, then stamp the source with
   the consolidation marker. Leave its substance unedited.

## Gates

Refuse, and report what is missing, when:

- The **caller or the primary agent** has no model and harness, or the entry
  would read as a bare "AI" (AI1). A descendant whose model the harness never
  exposed is `not recorded`, not a refusal.
- An AI-result has no derivation account (AI8).
- Agent review is being written up as human verification (AI10).
- Confidential third-party material — a referee report, a submission under
  review, private correspondence — was sent to a third-party model without
  the owner's permission (AI17). Record what was withheld instead.

**Requested ≠ observed model:** record both and flag the conflict in the
entry. Never silently rename a run to the model that was asked for.

Never infer an entry from memory. The record is evidence; an invented row
destroys its value.

## Report back

The record paths written, the entry ID, declared-tools rows added, sources
consolidated, any conflict or gate hit, and a reminder to run `update-tokens`
for the same ID if it has not run.
