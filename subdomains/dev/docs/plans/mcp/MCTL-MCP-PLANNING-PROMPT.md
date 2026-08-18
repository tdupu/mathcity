# Prompt: Plan The MathCity `mctl` CLI, MCP, And Dashboard Hardening

Status: prompt for a planning agent
Created: 2026-08-15
Repository: `/Users/tdupuy/repos/mathcity`
Requested output: an implementation plan, not code

## Your Assignment

Create a complete implementation plan for hardening the MathCity Mayor and
Clerk control surfaces by introducing a shared MathCity command core, a CLI
named `mctl`, a typed MCP server, and an eventual dashboard.

The purpose of this work is to replace loose prompt-skill command sequences
with a hardened domain interface. The first concrete focus is the brief
system, especially the current `check-briefs`, `present-briefs`,
`adjudicate-brief`, `create-brief`, and `mathcity.work` surfaces. The plan
must still cover the full affected skill set in the impact register.

Do not implement anything in this planning task. Produce a detailed,
reviewable implementation plan.

## Required Planning Order

The plan must be written in this order:

1. Dream end-state.
2. Domain model and source-of-truth model.
3. Full command, MCP, and dashboard control surface.
4. Diagnostics, invariants, traceability, and logging model.
5. Vertical-slice implementation ladder.
6. Skill refactor and post-implementation audit plan.
7. Testing and verification plan.
8. Commit and rollout strategy.

Do not start with the minimal vertical slice. First specify the desired system,
then carve it into vertical slices.

## Required Reading Before Planning

Read these files from the current repository state before writing the plan:

- `subdomains/dev/docs/plans/mcp/SKILL-IMPACT-REGISTER.md`
- `subdomains/brief-system/POLICY.md`
- `subdomains/brief-system/README.md`
- `assets/brief-pipeline/paths.toml`
- `assets/brief-pipeline/gates.toml`
- `formulas/brief-record-decision.toml`
- `formulas/work-briefed.toml`
- `formulas/commission-work-briefed.toml`
- `formulas/brief-prep.toml`
- `formulas/math-brief-prep.toml`
- `orders/brief-decision-dispatch.toml`
- `assets/bead-filter/dispatch-provenance-schema.toml`

Also inspect the current skills named in the impact register. The register is
the checklist of all prompt-skill surfaces this work may touch.

Before writing the plan, fetch the remote and confirm whether the repo is
behind `origin/main`. This work depends on recently changing brief-system
behavior.

## Current Coordination State

Treat the following as active context to verify, not as a substitute for
reading the files:

- BART has been working repo-side on the #38 decisions-track migration and
  fail-closed classifier behavior.
- QUIMBY has been working city/HQ-side and can report live migration state.
- #37 is the current deployed baseline for the unified stack-first pipeline.
- #38 is an active dependency for commands that import, list, or reason about
  legacy `.beads/decisions-track` rows.
- Bulk live decisions-track migration is held until the proof/canary work is
  green and Taylor authorizes it.

The plan must call out where #38 blocks or changes implementation order.

## Design Decisions Already Settled

Use these decisions as requirements.

### Architecture

- Build a shared MathCity core first.
- Implement the CLI first.
- Expose an MCP server over the same shared core.
- Build the dashboard later over the same backend.
- The CLI name is `mctl`.
- `mctl` is a MathCity domain tool, not a generic wrapper around shell, `gc`,
  or `bd`.
- `gc` and `bd` are implementation dependencies behind typed adapters.
- Do not scatter raw shell snippets throughout the implementation.

### Runtime Scope

- `mctl` is city-aware and rig-generic.
- MathCity is not special as a runtime scope. It is just one rig in a Gas City
  city.
- Plain commands operate on exactly one resolved rig.
- The city root is the HQ/root rig and is a valid single-rig scope.
- Cross-rig reads require an explicit option such as `--all-rigs`.
- Cross-rig mutations are forbidden unless a command-specific batch mode is
  explicitly designed later.
- Runtime scope comes from the Gas City city/rig/bead-store context, not from
  the source checkout that supplied the implementation.
- Running a normal brief/work command from a pack source checkout that is not a
  registered rig must hard-error with a concise context error.
- Source checkout paths matter only for diagnostics and implementation
  provenance, for example pointing to the formula or policy file that failed.

Example:

```bash
cd /Users/tdupuy/gt/mathcity
mctl briefs list
```

This should list briefs for the `mathcity` rig because that directory is a
registered rig.

```bash
cd /Users/tdupuy/repos/mathcity
mctl briefs list
```

This should hard-error because that directory is a pack/source checkout, not a
runtime rig, unless it is also explicitly registered as a city rig.

The error does not need to prove that the path is a source checkout. It only
needs to prove that the required runtime rig context is missing.

### Brief Source Of Truth

Use the adopted brief-system policy as the source of truth for rules.

The bead store is the canonical source of truth for brief state.

A brief is a `bd type=decision` bead. The brief bead is the decision bead.
There is no separate attached decision bead for brief adjudication.

Markdown files, frontmatter, `.beads/briefs/.pile`, `.beads/briefs/stack`,
`stack/.index.jsonl`, presentation files, archive files, and redundant
`decisions/*.toml` records are presentation/cache/redundancy artifacts. They
must reconcile to bead state.

Legacy `.beads/decisions-track/` is migration input and audit history, not the
normal presentation queue.

### Failure Philosophy

This work exists to prevent silent drift.

Read commands must not silently repair contradictions.

Read commands must not normalize away invariant violations.

Mutating commands must fail closed when invariant checks fail.

Examples of invariant violations:

- A closed/adjudicated brief appears in the presentable stack.
- A brief file exists with no corresponding `type=decision` bead.
- A brief bead lacks a source dependency.
- A verdict is recorded only in markdown or only in a redundant `.toml`, but
  not on the brief bead.
- A deferred brief appears before its defer window expires.
- The stack index names a missing file.
- Legacy decisions-track rows with unknown non-terminal status would be
  preserved invisibly.

The tool may offer explicit repair commands for bug recovery, but ordinary
read/list/show commands must not mutate as a side effect.

### Severity Model

Use severity classes:

- `INFO`: context only.
- `WARN`: degraded but safe; read commands may continue with a loud warning.
- `ERROR`: invariant violation; normal output or mutation is blocked.
- `FATAL`: unsafe or impossible to reason; stop immediately.

Be conservative.

### Diagnostics

Diagnostics should get as close as practical to Python error messages.

Every structured diagnostic should include:

- severity
- stable error code
- human message
- runtime city path
- runtime rig name/path
- bead id or brief slug when available
- data location, such as bead id, markdown path, index path and line
- policy reference, such as `subdomains/brief-system/POLICY.md:<line>`
- implementation provenance when available, such as formula, skill, or script
  path and line
- trace id
- suggested next command

For human output, prefer concise traceback-like blocks. For machine output,
support `--json`.

Policy messages should be surfaced with file and line references whenever the
implementation can identify them. If line numbers are not available for a
given policy mapping yet, the plan should include a task to introduce stable
policy IDs or a generated policy index.

### Traceability

Traceability is a core feature, not decoration.

Every top-level `mctl` CLI command and MCP tool call should receive a
`trace_id`.

The first version must at least record the initiating call that created or
mutated a brief.

Dream traceability should include:

- `trace_id`
- `operation_id`
- initiating command or MCP tool call
- initiated timestamp
- actor
- runtime city and rig
- source bead(s)
- brief bead
- brief slug
- producer formula
- producer formula step
- implementation source path when known
- input artifacts
- output artifacts
- planned effects
- actual effects

The dream feature should allow:

```bash
mctl trace show <trace-id>
mctl trace replay-preview <trace-id>
```

Do not block the first vertical slice on full replay. Capture the initiating
call and enough provenance to debug upstream failures, then iterate.

### MCP Best Practices

The MCP must be a typed, minimal, auditable tool surface.

Do not expose a generic `run_shell`, `run_gc`, `run_bd`, or
`run_mctl_command(command: string)` tool.

Expose small domain tools with strict schemas and structured outputs.

Use MCP tool annotations honestly:

- read-only tools marked read-only
- mutating tools marked non-read-only
- destructive and idempotent hints set conservatively
- closed-world/open-world hints set honestly

Mutating MCP tools must be compatible with host/client approval flows.

Use strict schemas with enums for verdicts, options, severities, and known
operation modes. Prefer output schemas and structured content. Tool error
results must be structured and must not hide invariant failures.

Start with a local stdio MCP server around the shared core. If a remote HTTP
MCP is ever planned, include proper authorization, token validation, HTTPS or
localhost rules, and per-client consent.

### Mutation Discipline

Normal CLI mutating commands may perform the mutation directly. Do not require
a mandatory `--apply` flow unless the plan gives a strong reason.

The shared core must still be factored around an internal effect plan so tests,
dashboard confirmation, MCP safety review, and debug modes can preview planned
effects.

CLI may expose this as `--dry-run` or `plan`, but dry-run is a testing and
debugging tool, not the central user model.

### Options In Briefs

Some briefs contain explicit options such as `(A)`, `(B)`, `(C)`, `(D)`.
The command and MCP surfaces must support this.

Dream commands:

```bash
mctl briefs options <brief>
mctl briefs show <brief> --option A
mctl briefs show <brief> --compare-options
mctl briefs adjudicate <brief> --verdict approve --option A --reason "..."
```

The parser should conservatively detect headings such as `Option A`, `(A)`,
`Alternative A`, and `Verdict A`. It must preserve raw snippets when uncertain.
It must not invent option labels. If a verdict is ambiguous because a brief has
multiple options, require an explicit option.

## Dream CLI Surface

The dream CLI should be designed before selecting the vertical slice.

Sketch the final CLI around these groups:

```bash
mctl context
mctl context --json

mctl briefs list
mctl briefs list --all-rigs
mctl briefs list --status pending
mctl briefs list --priority high
mctl briefs list --json

mctl briefs show <brief>
mctl briefs show <brief> --option A
mctl briefs show <brief> --compare-options
mctl briefs options <brief>

mctl briefs doctor
mctl briefs doctor <brief>

mctl briefs adjudicate <brief> --verdict approve --reason "..."
mctl briefs adjudicate <brief> --verdict approve --option A --reason "..."
mctl briefs adjudicate <brief> --verdict revise --reason "..."
mctl briefs adjudicate <brief> --verdict reject --reason "..."
mctl briefs defer <brief> --days 7 --reason "..."

mctl briefs create --source-bead <bead> --title "..."
mctl briefs create --source-kind manual --title "..." --body <path>
mctl briefs validate <brief-or-path>

mctl briefs repair <brief> --dry-run
mctl briefs repair <brief>

mctl work ready
mctl work status <bead>
mctl work dispatch <bead>
mctl work provenance <bead>

mctl trace show <trace-id>
mctl trace replay-preview <trace-id>
```

The plan may revise names, but it must explain why. Prefer conventional Unix
long options. Avoid overloaded single-letter flags where meanings are
ambiguous, for example `-a` for approve or `-r` for reject.

The canonical adjudication verb is `adjudicate`. Aliases like `approve`,
`revise`, or `reject` may be considered later, but the core command should be:

```bash
mctl briefs adjudicate ...
```

## Dream MCP Surface

Design the MCP as separate domain tools, not one generic command tool.

Expected dream tools:

- `context_resolve`
- `briefs_list`
- `briefs_show`
- `briefs_options`
- `briefs_doctor`
- `briefs_adjudicate`
- `briefs_defer`
- `briefs_create`
- `briefs_validate`
- `work_ready`
- `work_status`
- `work_dispatch`
- `work_provenance`
- `trace_show`
- `trace_replay_preview`

For `briefs_create`, the plan should decide whether to use one tool with a
`source_kind` enum or separate tools such as `briefs_create_from_bead` and
`briefs_create_manual`. Either is acceptable if the schema makes origin
explicit.

Every brief must have an origin, even if that origin is `manual`.

## Dream Dashboard Surface

The dashboard comes after CLI and MCP, but the plan should describe the dream
feature.

Expected dashboard capabilities:

- view current rig context
- list pending briefs
- inspect a full brief
- switch among options `(A)`, `(B)`, `(C)`, `(D)`
- compare options
- enter adjudication reason
- mark no-brainer leak or classifier issue
- save in-progress adjudication drafts
- run doctor checks
- show warnings/errors inline with policy references
- show trace/provenance for a brief
- submit verdict through the same shared core as CLI and MCP

Do not duplicate state parsing in the dashboard. It must call the shared core
or a service backed by the shared core.

## Domain Adapters

The shared core should isolate external tools behind typed adapters.

At minimum, plan these adapter boundaries:

- `ContextResolver`: resolves city, rig, bead store, and implementation
  provenance.
- `BeadStoreAdapter`: reads and writes canonical bead state, likely using `bd`
  or `gc bd` structured output where no library API exists.
- `GcOrchestratorAdapter`: calls Gas City orchestration surfaces such as work
  dispatch, formula metadata, events, or `gc sling` equivalents.
- `BriefCacheAdapter`: reads and writes derived brief artifacts, stack indexes,
  presentation records, archives, and redundant decision records.
- `PolicyIndex`: maps policy IDs and implementation checks to policy file
  locations.
- `TraceStore`: records command/MCP traces, effect plans, and actual effects.

Prefer direct library APIs if they exist and are stable. If the implementation
must call `gc` or `bd`, use structured JSON output and parse it with typed
schemas. Do not parse human tables when structured output exists.

## Initial Vertical Slices

Work vertically so the team can see end-to-end behavior early.

The plan should use this slice order unless source inspection strongly argues
otherwise:

### Slice 1: Context, Brief Read, Options, Doctor

Deliver:

- `mctl context`
- `mctl briefs list`
- `mctl briefs show`
- `mctl briefs options`
- `mctl briefs doctor`
- JSON output for tests
- structured diagnostics
- no mutations

Use a safe explicit fixture for read/show/options/doctor behavior. The current
known useful live fixture is:

```text
/Users/tdupuy/gt/.beads/briefs/stack/gsp-71p9fz-approach-a-blast-radius.md
```

This fixture is useful for read/show/revise-preview behavior. Do not use it as
an approve+dispatch fixture because its recommendation is revise.

### Slice 2: Brief Adjudication

Deliver:

- `mctl briefs adjudicate`
- verdict enum: `approve`, `revise`, `reject`
- defer path if practical, or a separate follow-up if it is too large
- option-aware adjudication
- effect-plan preview internally
- redundant decision record/cache update if still required by existing
  formulas
- `brief.decided` event behavior or whatever the current pipeline requires
- no-resurface invariant checks

The command must write the verdict on the brief bead itself and close the bead
for final verdicts. It must not create a second decision bead for a brief
adjudication.

### Slice 3: Work Ready And Dispatch

Deliver:

- `mctl work ready`
- `mctl work status <bead>`
- `mctl work dispatch <bead>`
- dispatch provenance
- duplicate dispatch checks
- automatic assignee/status verification where practical

This slice replaces the core of `mathcity.work`.

### Slice 4: Approval-To-Dispatch Integration

Deliver the end-to-end path where an approved brief can route work through the
hardened work dispatch boundary. Use a fixture or explicitly approved safe live
brief. Do not approve a live brief just because it is convenient.

### Slice 5: Brief Creation

Deliver:

- `mctl briefs create` from source bead/formula result
- manual brief creation with explicit manual origin
- validation against gate/frontmatter/schema requirements
- trace capture for the initiating call

Creation is in the dream spec from the beginning, but it does not need to be
the first implementation slice.

### Slice 6: MCP Adapter

Expose the already-working shared core through typed MCP tools. Do not add new
business logic in the MCP adapter.

### Slice 7: Dashboard

Build dashboard views after CLI and MCP semantics are stable. The dashboard
must use the same shared core/backend and should not become a second
implementation of the brief system.

## Skill Replacement Requirements

The implementation plan must include a task to revisit every skill and
non-skill surface in:

```text
subdomains/dev/docs/plans/mcp/SKILL-IMPACT-REGISTER.md
```

For each skill, the plan must decide one of:

- retire
- replace with `mctl` command docs
- keep as orientation wrapper over `mctl`
- keep unchanged with an explicit reason
- update to use MCP tool names once MCP is available

At minimum, the plan must cover:

- `check-briefs`
- `present-briefs`
- `adjudicate-brief`
- `create-brief`
- `work`
- `brief-prep`
- `catch-no-brainer`
- `decisions-to-briefs`
- `file-briefs`
- `present-it`
- `prime-clerk`
- `mayor-math-prime`
- `mayor-math`
- `mayor-math-restart`
- `mayor-math-handoff`
- `simple-work`
- `push-the-fleet`
- `refine-bead-manifest`
- `bead-check`
- `check-work`
- `check-molecules`
- `check-brief-policy`
- `check-build-formulas-and-skills`
- `gate-test-execution-silent`
- `improve-test-execution-silent`
- `grill-and-present`
- `xkcd-927`

The plan must also include a grep/audit task for lower-confidence references
to retired surfaces:

```text
check-briefs
present-briefs
adjudicate-brief
create-brief
mathcity.work
/work
brief-record-decision
gc dolt health
gc sling
bd close
decisions-track
```

## Testing Requirements

Plan tests at several levels:

- unit tests for context resolution
- unit tests for policy mapping and diagnostic construction
- unit tests for option parsing
- unit tests for severity classification
- unit tests for effect-plan construction
- fixture tests for brief list/show/options/doctor
- mutation tests using isolated temporary bead stores or fixtures
- integration tests against current `gc`/`bd` structured outputs where safe
- regression tests for no-resurface and defer-window behavior
- migration-dependent tests for legacy decisions-track behavior after #38
- MCP schema tests
- MCP approval/risk annotation tests if the chosen SDK supports them
- dashboard smoke tests only after dashboard implementation begins

Tests must not mutate live production beads unless the plan identifies a
specific authorized canary and a rollback/audit procedure.

## Plan Format Requirements

Write the final implementation plan as a Markdown file. Use checkbox tasks.
Each task should be independently reviewable and testable.

For each task include:

- files to create or modify
- interfaces produced and consumed
- failing test to write first
- implementation steps
- verification command
- commit boundary

Do not write placeholders such as `TBD`, `TODO`, `similar to above`, or
`add appropriate tests`. If a detail is unknown, include an explicit discovery
task that names the files and commands needed to resolve it.

## Rollout Requirements

The plan must include a rollout strategy:

1. Land shared core and read-only CLI.
2. Land brief adjudication behind tests and explicit fixtures.
3. Land work dispatch.
4. Convert the highest-risk skills to thin wrappers.
5. Add MCP adapter.
6. Update prime/clerk/mayor orientation surfaces.
7. Add dashboard.
8. Re-run the impact register audit.
9. Send the final diff/checklist to BART and QUIMBY for review before
   retiring old skills.

## Non-Goals For The First Implementation Plan

Do not plan to:

- build a generic Gas City MCP
- expose arbitrary bash through MCP
- expose arbitrary `gc` or `bd` through MCP
- silently repair drift during read commands
- bulk-migrate live decisions-track data without #38 proof/canary approval
- make the dashboard the first deliverable
- rewrite the entire brief pipeline before a read-only vertical slice works

## Success Criteria

The plan is successful if another agent can implement it task by task and
produce:

- a working `mctl briefs list/show/options/doctor` path
- a working `mctl briefs adjudicate` path
- a working `mctl work ready/status/dispatch` path
- structured diagnostics with policy/data/provenance references
- trace IDs on top-level operations
- typed adapters around `gc` and `bd`
- a typed MCP surface over the shared core
- an updated skill set that no longer teaches loose prompt-only command chains
  as the operational API

