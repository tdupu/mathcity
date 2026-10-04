---
name: frontier-dump
description: Delegate a prompt to the best available frontier agent and save a dated research dump under ai/.
---

# Frontier Dump

Use this skill when the user wants a prompt handed to the strongest
available research-grade agent and the result recorded as a durable, dated
scratch package. This skill was formerly named `astra-dump`; it no longer
hardcodes a single model — "frontier" means whichever reasoning-strong
model is actually the best one reachable from the current harness, decided
at run time, not fixed at write time.

## Workflow

1. Read the nearest `AGENTS.md` for the active workspace and inspect one or
   two existing `ai/` dumps to copy their conventions (older dumps may still
   sit under `scratch/`; read those, write new ones to `ai/`). Preserve unrelated
   work and do not create a bead unless the user asks for task tracking.
2. Derive the active local date as `YYYY-MM-DD` and a short lowercase
   hyphenated slug from the user's prompt. Use
   `ai/YYYY-MM-DD-<slug>/`. Never overwrite an existing dump: append a
   short numeric suffix when the target already exists.
3. Identify the best available frontier-tier model reachable from the
   current harness — the strongest general-purpose reasoning model you can
   actually invoke right now. This varies by harness and changes over time;
   never hardcode a specific model id in this skill. If the current harness
   exposes a distinguished top-tier model (e.g. a named "frontier" or
   "max reasoning" agent option), use it; otherwise use the strongest model
   this session can delegate to. Delegate the prompt to a primary subagent
   using that model with a strong reasoning setting appropriate to the
   problem.
4. Confine writes to the new dump folder except accounting consolidation below.
   Preserve existing files otherwise; use additional subagents only when
   useful, with disjoint write scopes.
5. Pass the user's prompt verbatim or faithfully, together with the output
   folder, date, source/workspace scope, and the artifact requirements below.
   Also
   pass the negative-result obligation explicitly: the worker must report what
   it *refuted* — claims of the prompt or of the input corpus that turn out to
   be false, expectations that fail, proposed definitions that are ill-posed,
   counterexamples found — as first-class findings with their proofs, not as
   caveats (ST11; LX11/LX12 where a mathcity pack is installed).
   Do not silently broaden the requested research or authorize commits, pushes,
   issue changes, or manuscript edits.
6. Wait for the primary worker to finish. If required artifacts are missing,
   send one focused follow-up asking it to complete the package; do not invent
   missing results locally.
7. Validate locally: check required files exist, run supplied verification
   scripts and `git diff --check` when relevant. Confirm writes stayed inside
   the dump folder except the accounting consolidation below.

## Required dump

The folder must contain:

- `report.md`: a self-contained report with status, the question-to-answer
  map, definitions, derivations or counterexamples, source locators,
  verification, limitations, and unresolved questions. Separate proved,
  conditional, computational, and conjectural claims. It must contain an
  explicit **refutations and corrected expectations** section: every claim the
  work disproved, every expectation that failed, every ill-posed proposal, and
  every counterexample, each stated as a finding with the expectation it
  corrects named ("it was natural to expect $X$; in fact $Y$") and its proof,
  counterexample, or computation. If neither work nor inputs contain negative
  findings, explicitly report zero. For a missing section or omitted or buried
  findings, follow up under step 6.
- The dump's usage and cost records, as working records for the folder: a
  per-dump `ai-usage.md` and `tokens.md`. This skill does not define their
  schemas or write them directly — **delegate**. [[update-ai-usage]] owns the
  provenance record (date and timezone, human prompt and direction, per-agent
  model and harness from the caller through every descendant, work performed,
  sources and computations, AI-results with their derivation accounts and
  literature-search outcomes, review and integration status, scope limits) and
  mints the task ID. [[update-tokens]] owns the priced record (token classes,
  rates with their date basis, computed cost, estimates labelled as estimates,
  never invented) and prices against that ID.

Accounting exception: both delegates must consolidate this task's records into
the repository's single master `ai-usage.md` and `tokens.md` (AI15), preserving
unrelated entries and per-dump files as evidence. No competing ledger or
duplicate schemas; follow `<repo>/AI-POLICY.md` (template:
`mathcity/subdomains/repo-docs/templates/AI-POLICY.md`).

## Negative-result transfer (ST11, LX11/LX12)

A dump is an artifact produced from previous work, so it inherits the
negative-result floor: ST11 of the STYLE template, which states the rule in
full without requiring a pack, and LX11/LX12 of
`mathcity/subdomains/latex/POLICY.md` where one is installed. Two
obligations, both checkable:

1. **Carry forward.** Every refutation, counterexample, and failed-expectation
   finding in the dump's inputs (prior reports, reviews, ledgers, prompts,
   superseded drafts) appears in the new `report.md`, or is listed there with
   the authorized reason it is out of scope. Report the counts carried and
   excluded.
2. **Carry outward.** When the dump is later consumed — promoted into a
   manuscript, summarized, merged, or handed off — its refutations travel with
   its theorems. Prompts that say "write up the results" mean the negative
   ones too. Refutations are the findings most easily lost across a handoff and
   the most expensive to re-derive, so they are transferred first.

Never resolve a conflict between a prompt's assertion and the work's finding by
deleting the finding: record that the prompt's assertion is false, with the
evidence.

## Model and provenance rules

Record exact model strings, never informal labels alone — "the best frontier
agent" is how you CHOOSE the worker, never how you RECORD it. The Agents
table in [[update-ai-usage]] is where these land, one row per agent: role,
agent ID, requested model (a concrete id such as `gpt-6-astra` or
`claude-opus-5`), the model the runtime actually reported, harness, and
reasoning effort. A requested/observed conflict is recorded as a conflict,
never resolved silently in favour of the label. Dates are ISO 8601 with
offset. AI1 is the governing rule; this skill supplies the facts, the
delegate owns the format.

The primary worker may use primary literature, local files, and permitted
read-only tools within the user's scope. External sources must be cited in
`report.md`; unverified references and failed retrievals must be labeled.
Research artifacts are not human- or independently-reviewed unless the dump
actually records such review.

## Completion response

For later synthesis, hand the consumer the report and its evidence paths.
`create-exposition` gathers an explicit selection of dumps into a source-linked
spec; `math-workflow` then coordinates `rapid-prototype`, `fill-in-prototype`,
independent reviews and manuscript integration through the powers routers.
Keep this dump intact. Follow-up research creates another package; selection
and manuscript promotion belong to that consuming workflow. A dump request
alone ends here, without starting a manuscript or importing a browser chat.

Report the absolute dump-folder link, files created, primary and descendant
model identities, verification performed, unresolved limits, and whether any
changes outside the folder occurred. Do not claim publication, commit, or push.
