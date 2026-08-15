# MCP Hardening Skill Impact Register

Status: pre-implementation audit register
Created: 2026-08-15
Repository: `/Users/tdupuy/repos/mathcity`
Requested location: `mathcity/dev/docs/plans/mcp/`
Repo location: `subdomains/dev/docs/plans/mcp/`

## Purpose

This file is the checklist of MathCity skills and adjacent surfaces touched by
the planned `mctl` / MCP hardening work. The goal is to make sure every prompt
skill that currently relies on loose shell snippets, hand-slinging, or
brief-pipeline lore is revisited after the shared core, CLI, MCP adapter, and
eventual dashboard are implemented.

The register is intentionally broader than the first vertical slice. Some
skills should be replaced by commands, some should become thin documentation
wrappers over commands, and some only need wording or cross-reference updates.
Nothing in this register authorizes live `.beads` migration or live brief
adjudication.

## Coordination State

- BART (`80b87468`, repo-side, `/Users/tdupuy/repos`) reviewed the scope on
  2026-08-15. Current main is `cb32258`, deployed by pull. BART reported that
  #37 changed `present-briefs`, `prime-clerk`, `decisions-to-briefs`,
  `brief-check.sh`, `gates.toml`, `brief-shuffle.toml`,
  `brief-producer-failure-record.toml`, `brief-decisions-track-inventory.py`,
  brief docs, policy, and tests.
- QUIMBY (`ddc2c0df`, mayor/HQ-side, `/Users/tdupuy/gt`) reviewed the live
  migration state. #38 Fix A is ruled: fail closed. Unknown non-terminal
  decisions-track statuses must migrate to a visible pile entry rather than be
  preserved invisibly.
- BART owns #38 repo-side implementation. This register must not duplicate
  that work. Expected #38 file changes are limited to
  `assets/scripts/brief-decisions-track-inventory.py` and
  `tests/decisions-track-migration/` unless BART reports otherwise.
- Bulk live `.beads` decisions-track migration is still HELD until proof 5 goes
  green and Taylor authorizes the live canary and migration.

## Active Dependencies

- #37 is the current deployed baseline. The MCP/CLI plan should model the
  unified stack-first pipeline, not the pre-#37 decisions-track path.
- #38 is an active dependency for any command that imports, lists, or reasons
  about legacy decisions-track rows. The post-MCP checklist must be re-run
  after fail-closed classifier behavior and proof 5 land.
- Current first fixture for safe `list/show/revise --dry-run` work:
  `/Users/tdupuy/gt/.beads/briefs/stack/gsp-71p9fz-approach-a-blast-radius.md`.
  This is a live approved brief with `server_touching: false` and
  `user_skill_touching_override: false`, but its recommendation is `revise`,
  not approve.
- `gs-nduq-investigate-brief.md` is useful later for safety-gate behavior
  because it recommends approve but carries `user_skill_touching_override:
  true`.

## Expected Command Surface

Working name: `mctl`, backed by a shared core library.

- CLI first: implement `mctl briefs ...` and `mctl work ...` over the shared
  core.
- MCP second: expose typed MCP tools that call the same core functions.
- Dashboard later: read and mutate through the same backend, not by duplicating
  filesystem or `gc` command logic.
- `gc` and `bd` remain implementation dependencies. The MathCity tool should
  harden MathCity domain operations, not become a generic Gas City MCP.

## Primary Replacement And Hardening Targets

### `check-briefs`

- Path: `skills/check-briefs/SKILL.md`
- Current role: reports ready, approved stack briefs in a compact table.
- Why touched: it uses stale `gc dolt health` preflight and scans markdown
  frontmatter directly, while #37 made the stack index the presentation
  queue. Live data can contain stale index rows, missing files, or
  non-ready frontmatter.
- Expected disposition: replace with `mctl briefs list` and `mctl briefs
  doctor`. The command must reconcile stack index, file existence,
  frontmatter, defer windows, and live bead status.
- Post-work audit:
  - Skill no longer includes raw `gc dolt health`.
  - Skill points to `mctl briefs list` for normal use.
  - Doctor output reports stale index rows separately from ready briefs.
  - Tests include the `gsp-71p9fz` ready/revise fixture shape and a stale row.

### `present-briefs`

- Path: `skills/present-briefs/SKILL.md`
- Current role: presents one full brief at a time and records the human
  verdict through `brief-record-decision`.
- Why touched: this is the clerk-facing control surface for queue selection,
  full-text rendering, no-brainer leak capture, and verdict recording.
- Expected disposition: replace the operational parts with `mctl briefs next`,
  `mctl briefs show`, and `mctl briefs verdict`. Keep the skill, if at all, as
  a thin orientation wrapper for humans and agents.
- Post-work audit:
  - One-brief-at-a-time invariant preserved.
  - Full-text presentation preserved when requested.
  - Legacy decisions-track fallback is gated by #37/#38 migration state.
  - No direct filesystem mutation outside the shared core.
  - Verdict flow still writes through `brief-record-decision` semantics.

### `adjudicate-brief`

- Path: `skills/adjudicate-brief/SKILL.md`
- Current role: records decisions and fork-dispatches approval work.
- Why touched: it has overlapping concepts with `present-briefs` and includes
  direct `bd` commands plus an approve path that drifts from `mathcity.work`.
- Expected disposition: replace brief verdict recording with `mctl briefs
  verdict`. Standalone decision creation may remain, but should be clearly
  separated from brief verdicts.
- Post-work audit:
  - Brief verdicts do not create a second decision bead.
  - Approve/reject/revise/defer are typed command choices.
  - No direct `bd close`, `bd defer`, or manifest rewrites remain in routine
    agent-facing instructions.
  - Approve dispatch routes through hardened `mctl work dispatch` or the
    brief-decision-dispatch event edge, not hand-slung formula snippets.

### `create-brief`

- Path: `skills/create-brief/SKILL.md`
- Current role: drafts durable gated `.md` brief artifacts for code artifacts
  and blocked-worker escalation.
- Why touched: it owns frontmatter, lane selection, gate evidence, path
  selection, escalation behavior, and several known pipeline conflicts. The
  deposit path is explicitly contested in the skill text.
- Expected disposition: move operational logic into `mctl briefs create` and
  `mctl briefs validate`, backed by a single parser/schema for frontmatter and
  gate evidence.
- Post-work audit:
  - Pile/stack paths come from `assets/brief-pipeline/paths.toml` or shared
    core configuration, not prose.
  - G14 tri-state and checker behavior are reconciled.
  - Escalation lane remains fail-closed and never auto-approvable.
  - Standalone runs clearly report when brief-record bookkeeping is absent.

### `work`

- Path: `skills/work/SKILL.md`
- Current role: Mayor-facing `mathcity.work` dispatch wrapper over
  `work-briefed`.
- Why touched: this is the main workhorse boundary. It has stale `gc dolt`
  preflight and raw `gc sling` snippets, then asks the agent to verify
  assignment manually.
- Expected disposition: replace with `mctl work dispatch`, `mctl work status`,
  and `mctl work provenance` over a shared core.
- Post-work audit:
  - Preflight uses current `gc`/service interfaces.
  - Formula discovery and artifact-root construction are typed.
  - Assignee verification and dispatch-provenance event creation are automatic.
  - Duplicate dispatch checks are in the command, not left to prompt memory.

## Brief Pipeline Dependencies

### `brief-prep`

- Path: `skills/brief-prep/SKILL.md`
- Current role: end-to-end brief-prep worker composing tests, gate checks,
  no-brainer classification, drafting, review, and bookkeeping.
- Why touched: it is upstream of every created brief and will need to call or
  match the same shared core as `create-brief`.
- Expected disposition: refactor to invoke `mctl briefs prepare` or to become
  documentation for the formula/command path.
- Post-work audit: frontmatter schema, gate evidence, override computation,
  pile deposit, and bookkeeping all match the command implementation.

### `catch-no-brainer`

- Path: `skills/catch-no-brainer/SKILL.md`
- Current role: classifier for no-brainer and capability-blocker brief shapes.
- Why touched: `create-brief`, `brief-prep`, `present-briefs`, and gate
  profiles consume its output.
- Expected disposition: expose classifier behavior through shared core,
  probably `mctl briefs classify`, while keeping the skill as policy
  documentation if useful.
- Post-work audit: classifier output remains machine-readable and compatible
  with profile-specific G9/N9 requirements.

### `decisions-to-briefs`

- Path: `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`
- Current role: converts pending decisions outside the main brief pipeline
  into adjudicable brief artifacts.
- Why touched: #37 made decisions-track a migration fallback, and #38 changes
  how unknown non-terminal legacy statuses are classified.
- Expected disposition: replace operational parts with `mctl briefs import`
  or `mctl briefs create-decision`, gated by migration state.
- Post-work audit: no command can strand non-terminal decisions-track rows in
  an invisible preserve state.

### `file-briefs`

- Path: `skills/file-briefs/SKILL.md`
- Current role: async onboarding/decision filing flow that delegates to
  `brief-prep` and surfaces via `present-briefs`.
- Why touched: it is a batch producer/consumer of the exact surfaces being
  hardened.
- Expected disposition: update to use `mctl briefs prepare-batch` and
  `mctl briefs list/next`.
- Post-work audit: no direct `/present-briefs` or `/adjudicate-brief` calls
  remain unless they are clearly legacy aliases.

### `present-it`

- Path: `skills/present-it/SKILL.md`
- Current role: terminal-only presentation sibling that supplies the brief
  section structure.
- Why touched: it defines output shape used by `create-brief` and
  `brief-prep`, but should not become a mutation surface.
- Expected disposition: keep as presentation/template policy; do not route
  state changes through it.
- Post-work audit: references distinguish terminal presentation from
  command-backed brief file creation.

### `check-brief-policy`

- Path: `subdomains/brief-system/skills/check-brief-policy/SKILL.md`
- Current role: policy checker for brief-system surfaces.
- Why touched: it references brief stack layout and policy invariants that
  commands will enforce mechanically.
- Expected disposition: update to call `mctl briefs doctor` or check the same
  shared schema.
- Post-work audit: old manifest/path assumptions are corrected for #37 and
  #38.

## Mayor And Clerk Orientation Surfaces

### `prime-clerk`

- Path: `skills/prime-clerk/SKILL.md`
- Current role: clerk orientation for present, record, and dispatch flow.
- Why touched: it explicitly teaches `present-briefs -> adjudicate-brief ->
  mathcity.work`.
- Expected disposition: replace that flow with `mctl briefs next/show/verdict`
  and `mctl work dispatch`, or with MCP tool names once available.
- Post-work audit: no stale direct sling examples, no stale decisions-track
  wording, and no instruction to edit the wrong checkout.

### `mayor-math-prime`

- Path: `skills/mayor-math-prime/SKILL.md`
- Current role: primes outside Mayor sessions with MathCity operating rules.
- Why touched: it names the brief and work skills that are being hardened.
- Expected disposition: update prompt templates to describe command/MCP
  control surfaces instead of relying on skill prose as the operational API.
- Post-work audit: templates in `skills/mayor-math-prime/templates/` match the
  new surface.

### `mayor-math`

- Path: `skills/mayor-math/SKILL.md`
- Current role: Mayor dispatch doctrine and routing rules.
- Why touched: it frames when and how `mathcity.work` and brief adjudication
  are used.
- Expected disposition: update dispatch doctrine around `mctl work` and typed
  brief commands.
- Post-work audit: restart injection scripts and prompt text are consistent.

### `mayor-math-restart`

- Path: `skills/mayor-math-restart/SKILL.md`
- Current role: restart cycle around mayor handoff and prime.
- Why touched: the restarted Mayor must not be re-primed into old skill-only
  control surfaces.
- Expected disposition: update if prompt generation still references retired
  commands.
- Post-work audit: generated restart prompt uses the same command names as
  `mayor-math-prime`.

### `mayor-math-handoff`

- Path: `skills/mayor-math-handoff/SKILL.md`
- Current role: session handoff for Mayor state.
- Why touched: handoff instructions must record any in-flight command/MCP
  work, not just loose skill calls.
- Expected disposition: update handoff checklist after `mctl` exists.
- Post-work audit: handoff names active work, pending briefs, and migration
  holds in command-readable terms.

## Work Dispatch Wrappers And Related Checks

### `simple-work`

- Path: `skills/simple-work/SKILL.md`
- Current role: lightweight alternative to `mathcity.work` for bounded work.
- Why touched: it ends by landing a brief on the stack and references
  `check-briefs` / `present-briefs`.
- Expected disposition: update to use `mctl work` or explicitly remain a
  formula-oriented bypass for simple work.
- Post-work audit: final surfacing instructions use command-backed brief
  listing and presentation.

### `push-the-fleet`

- Path: `subdomains/dev/skills/push-the-fleet/SKILL.md`
- Current role: batch layer over `mathcity.work`.
- Why touched: it duplicates preflight language and routes multiple beads into
  the same dispatch boundary.
- Expected disposition: replace operational dispatch with `mctl work batch`.
- Post-work audit: no stale `gc dolt health`; batch dispatch inherits the same
  duplicate and provenance gates as single dispatch.

### `refine-bead-manifest`

- Path: `skills/refine-bead-manifest/SKILL.md`
- Current role: turns bead-manifest classifications into follow-up work,
  decisions, or dispatch batches.
- Why touched: it routes `DISPATCH_NOW`, `DISPATCH_BATCH`, and `DECISIONS`
  through `mathcity.work` and `decisions-to-briefs`.
- Expected disposition: update routes to command-backed dispatch and brief
  creation.
- Post-work audit: no direct skill invocation is required for routine
  dispatch or decision filing.

### `bead-check`

- Path: `skills/bead-check/SKILL.md`
- Current role: checks suspicious beads and can route architecture judgments
  toward adjudication.
- Why touched: it names `mathcity.work` as suspected source/provenance and
  references adjudication routing.
- Expected disposition: update to consume `mctl work provenance` and typed
  verdict records.
- Post-work audit: classifications match the new dispatch provenance schema.

### `check-work`

- Path: `skills/check-work/SKILL.md`
- Current role: work health check.
- Why touched: `work` points users here when dispatch verification or
  assignee state is unclear.
- Expected disposition: either wrap `mctl work status` or become a thin guide
  to it.
- Post-work audit: status checks can answer whether a dispatched bead is
  claimed, stranded, commissioned, or waiting on a brief.

### `check-molecules`

- Path: `skills/check-molecules/SKILL.md`
- Current role: molecule/workflow health inspection.
- Why touched: it references dispatch ownership and distinguishes check-only
  from work-pushing.
- Expected disposition: update terminology and links to `mctl work status`
  where appropriate.
- Post-work audit: no instruction conflicts with the hardened dispatch path.

## Policy, Gate, And Support Skills

### `check-build-formulas-and-skills`

- Path: `subdomains/dev/skills/check-build-formulas-and-skills/SKILL.md`
- Current role: validates MathCity-owned briefed/work-boundary formulas and
  skills.
- Why touched: this is the natural post-change gate to ensure skills stop
  naming retired loose surfaces.
- Expected disposition: add checks or checklist entries for `mctl`/MCP
  migration once command names are final.
- Post-work audit: every skill in this register is either updated or has a
  documented reason to remain unchanged.

### `gate-test-execution-silent`

- Path: `skills/gate-test-execution-silent/SKILL.md`
- Current role: gate around missing or silent test evidence.
- Why touched: `create-brief` and `brief-prep` refer to G14 behavior, and
  command validation should make this mechanical.
- Expected disposition: encode required evidence in brief validation.
- Post-work audit: G14 token behavior and checker behavior no longer
  contradict each other.

### `improve-test-execution-silent`

- Path: `skills/improve-test-execution-silent/SKILL.md`
- Current role: remediation path for silent test-evidence failures.
- Why touched: it is downstream of the same G14 surface.
- Expected disposition: update remediation to point at `mctl briefs validate`
  output and fix commands.
- Post-work audit: failure messages tell agents exactly what evidence is
  missing.

### `grill-and-present`

- Path: `skills/grill-and-present/SKILL.md`
- Current role: older gated presentation flow with proposed retirement.
- Why touched: it is explicitly superseded by `create-brief` and
  `present-it` in current doctrine.
- Expected disposition: retire or update final references so it does not
  compete with command-backed brief creation.
- Post-work audit: no xkcd-927 duplicate standard remains on the brief surface.

### `xkcd-927`

- Path: `skills/xkcd-927/SKILL.md`
- Current role: handles duplicate/competing standards and cites
  `adjudicate-brief`.
- Why touched: hardening is explicitly meant to replace multiple loose
  standards with one command/MCP surface.
- Expected disposition: update canonical-decision examples to use the
  hardened verdict command.
- Post-work audit: reconciling decisions still go through canonical decision
  records, not ad hoc markdown.

## Lower-Confidence Audit Hits

These appeared in grep searches or are adjacent to dispatch/brief policy. They
may not require edits, but they should be checked after implementation.

- `skills/intercept-bead/SKILL.md`
- `skills/revise-artifact/SKILL.md`
- `subdomains/dev/skills/formula-work/SKILL.md`
- `subdomains/dev/skills/audit-recent-work/SKILL.md`
- `subdomains/dev/skills/hourly-check/SKILL.md`
- `subdomains/dev/skills/city-status/SKILL.md`
- `subdomains/dev/skills/check-zero/SKILL.md`
- `subdomains/dev/skills/strand-sweep/SKILL.md`
- `subdomains/latex/skills/check-labels-and-refs/SKILL.md`

Post-work audit for this bucket:

- Search for retired names: `check-briefs`, `present-briefs`,
  `adjudicate-brief`, `create-brief`, `mathcity.work`, `/work`,
  `brief-record-decision`, and stale `gc dolt` snippets.
- For each hit, decide one of: update to `mctl`, keep as historical context,
  or mark as unrelated.

## Non-Skill Critical Surfaces

These are not skills, but the command/MCP plan touches their behavior or must
remain compatible with them.

### Changed by #37 and current baseline

- `skills/present-briefs/SKILL.md`
- `skills/prime-clerk/SKILL.md`
- `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`
- `assets/scripts/checks/brief-check.sh`
- `assets/brief-pipeline/gates.toml`
- `formulas/brief-shuffle.toml`
- `formulas/brief-producer-failure-record.toml`
- `assets/scripts/brief-decisions-track-inventory.py`
- `README-clerk.md`
- `subdomains/brief-system/README.md`
- `docs/testing-guide.md`
- `subdomains/brief-system/POLICY.md`
- `subdomains/dev/POLICY-city.md`
- `tests/unified-brief-pipeline-e2e/`
- `tests/decisions-track-migration/`
- `tests/unified-brief-gate-profiles/`
- `tests/present-briefs-unified-source/`
- `tests/brief-quality-failure/`
- `tests/present-briefs-defer-filter/`

### Active #38 dependency

- `assets/scripts/brief-decisions-track-inventory.py`
- `tests/decisions-track-migration/`

### Existing brief/work formulas and orders to preserve

- `formulas/brief-record-decision.toml`
- `formulas/brief-present-next.toml`
- `formulas/work-briefed.toml`
- `formulas/commission-work-briefed.toml`
- `formulas/brief-prep.toml`
- `formulas/math-brief-prep.toml`
- `formulas/brief-watchdog-refill.toml`
- `formulas/file-or-sendback-route.toml`
- `orders/brief-shuffle-pile.toml`
- `orders/brief-decision-dispatch.toml`
- `orders/brief-watchdog-refill.toml`
- `orders/brief-watchdog-refill-on-stack-low.toml`
- `orders/post-decision-file-or-sendback.toml`
- `assets/brief-pipeline/paths.toml`
- `assets/brief-pipeline/file-or-sendback-log-spec.md`
- `assets/bead-filter/dispatch-provenance-schema.toml`
- `assets/bead-filter/lost-bead-schema.toml`

## Post-Implementation Checklist

Run this checklist after the shared core, CLI, MCP adapter, or dashboard land.

1. Re-run grep over all skills for retired loose surfaces:
   `check-briefs`, `present-briefs`, `adjudicate-brief`, `create-brief`,
   `mathcity.work`, `gc dolt health`, raw `gc sling`, direct `bd close`, and
   direct decisions-track manifest rewrites.
2. For each primary target, decide whether the skill is removed, retained as
   orientation, or converted to a command wrapper.
3. Verify `mctl briefs list` reconciles index, files, frontmatter, defer
   windows, and live bead status.
4. Verify `mctl briefs show` can present the explicit fixture
   `gsp-71p9fz-approach-a-blast-radius` without mutating live state.
5. Verify `mctl briefs verdict --dry-run revise` reports the exact effects
   for the `gsp-71p9fz` fixture.
6. After #38 lands, verify proof 5 is green for the migration inventory and
   that no non-terminal legacy row is preserved invisibly.
7. Verify `mctl work dispatch` creates or records dispatch provenance and
   detects empty assignee after the verification window.
8. Verify `prime-clerk` and `mayor-math-prime` no longer teach agents to use
   loose skill chains as the operational API.
9. Verify documentation distinguishes CLI, MCP, and dashboard roles over the
   same shared core.
10. Send the updated checklist or diff back to QUIMBY and BART for final
    review before removing or retiring any skill.
