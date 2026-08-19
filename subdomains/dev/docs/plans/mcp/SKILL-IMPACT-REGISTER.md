# MCP Hardening Skill Impact Register

Status: pre-implementation audit register
Created: 2026-08-15
Repository: `<repos-root>/mathcity`
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

- BART (`80b87468`, repo-side, `<repos-root>`) reviewed the scope on
  2026-08-15. Current main is `cb32258`, deployed by pull. BART reported that
  #37 changed `present-briefs`, `prime-clerk`, `decisions-to-briefs`,
  `brief-check.sh`, `gates.toml`, `brief-shuffle.toml`,
  `brief-producer-failure-record.toml`, `brief-decisions-track-inventory.py`,
  brief docs, policy, and tests.
- QUIMBY (`ddc2c0df`, mayor/HQ-side, `<city-root>`) reviewed the live
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
  `<city-root>/.beads/briefs/stack/gsp-71p9fz-approach-a-blast-radius.md`.
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

---

# Final Dispositions — Slice 7 (2026-08-19)

Slice 7 is the skill refactor onto the `mctl` surface. Everything above this
line is the **pre-implementation** audit; this section is the **audit record**
required by plan §6 ("Audit Output Format") and Slice 7 step 6.

## How to read a disposition

| Token | Meaning |
| --- | --- |
| `replace-with-mctl` | the skill's operational core was hand-rolled state manipulation; `mctl` now performs it |
| `wrap-with-mctl` | the skill keeps its own job but calls `mctl` for the canonical read or the canonical write inside it |
| `no-change` | the skill touches neither adapter's state, or its writes are outside both. **Every such row cites the §2 boundary that makes it legitimate** — `BeadStoreAdapter` (canonical) or `BriefCacheAdapter` (derived) |
| `blocked-by-policy` | migrating it would change live state this plan holds frozen (#38, decisions-track), or the command it needs does not exist |

`no-change` is a real verdict, not a shrug. Plan audit rule 3 admits it "only
when the skill never touches brief/work state or when it is explicitly
read-only and already respects the canonical bead-first model" — so each one
below names which of those two it is, in §2's vocabulary.

## Wiring facts, verified in this repo on 2026-08-19

Before the slice, **`check-briefs` was the only skill in the repository that
named `mctl` at all** (24 mentions). Every other skill — including
`mayor-math-prime`, `mayor-math`, `prime-clerk`, `work`, `simple-work`,
`formula-work`, `testing-work` — had zero. The CLI and the MCP server were
typed and tested with nothing an agent runs pointing at them.

Skills are prompt text executed as shell, so **every wiring below targets
`bin/mctl`, not the MCP server.** The MCP surface exists for typed programmatic
clients (the dashboard is one), and its rollout gate defaults external clients
to zero tools; a bash block is the wrong caller for it.

The canonical call-site block lives in
[`template-fragments/mctl-entry-point.md`](../../../../template-fragments/mctl-entry-point.md)
and is copied verbatim into each wired skill, matching the `check-briefs` pilot.
`tests/mctl-shim-callsite/smoke_test.sh` greps every wired skill for it.

## The table

| Skill | Current behavior (before Slice 7) | Disposition | MCTL surface | Trace behavior | Verification | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| `check-briefs` — `skills/check-briefs/SKILL.md` | per-brief `bd show` loop parsing a `^Status:` line that `bd` 1.1.0 no longer emits, so the filter was a silent no-op | `replace-with-mctl` (pilot, pre-existing) | `mctl briefs list --json` once per rig; `decision_state` is the filter | read-only; no trace reported | `tests/mctl-shim-callsite/smoke_test.sh` parts 2, 4 | `gt-*` beads keep a direct `bd` fallback whose `^Status:` parse is still broken; frontmatter fields (`unlock_count`, `deposited_at`, `epic`) are unmodelled in `mctl_core` and still scanned from disk |
| `adjudicate-brief` — `skills/adjudicate-brief/SKILL.md` | fork body ran `bd comments add` + `bd close`/`bd defer`, rewrote the brief's `status:` frontmatter in place, rewrote the legacy decisions-track manifest, then hand-slung `build-basic-briefed` and eyeballed an assignee grep | `replace-with-mctl` (verdict + dispatch) / `blocked-by-policy` (step 2b, legacy decisions-track sync) | `mctl briefs adjudicate` / `mctl briefs defer` (`--dry-run` preview first); `mctl work status` + `mctl work dispatch` on approve | fork emits `MCTL-TRACE: <id>` per mutation and repeats them in its one-line summary | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-6; `tests/present-briefs-defer-filter/test_defer_filter.sh` executes step 2b's writer; `tests/artifact-root-scoping/smoke_test.sh` | **step 2b survives as the one declared cache-write exemption** — `BriefCacheAdapter`'s legacy decisions-track rows are #38's lane and `mctl` models neither the file nor the manifest, so deleting the sync hands the job to nobody and re-opens the measured #18 re-presentation bug. It runs after the mctl write and touches decisions-track only. `gt-*` verdicts have no `mctl` route and are escalated instead |
| `create-brief` — `skills/create-brief/SKILL.md` | chose its own deposit path, contested three ways between this skill, `paths.toml`, and `brief-prep`, and told the agent to "record which path you chose" | `replace-with-mctl` (code-artifact lane) | `mctl briefs create --body-file` then `mctl briefs validate` | `MCTL-TRACE: <id>` from the create payload | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-6 | the escalation lane keeps a **declared** direct filesystem write — `mctl briefs create` shells out to `bd`, which is usually the thing that failed; it must try `--dry-run` first and name the diagnostic that forced the fallback |
| `brief-prep` — `skills/brief-prep/SKILL.md` | Phase 3 hand-placed `.pile/<slug>.md` and Phase 5 edited that deposited file in place | `replace-with-mctl` (deposit only) | Phase 3 drafts to `.staging/`; new Phase 5c runs `mctl briefs create --body-file` + `mctl briefs validate` | `MCTL-TRACE: <id>` in the Phase 7 return block, alongside the brief bead id | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-6 | gate-flag frontmatter (`status`, `review_gate`, `unlock_count`, `## Gate Evidence`) is unmodelled in `mctl_core`, so Phases 3-5 still own it — on the staged copy, before deposit |
| `coordinate-review` — `skills/coordinate-review/SKILL.md` | artifact-agnostic FP loop; when the artifact was a brief the critic could not see the bead behind it | `wrap-with-mctl` | `mctl briefs doctor --brief` + `mctl briefs options`, read-only, folded into the critic prompt as evidence | read-only; no mutation, no trace reported | `tests/mctl-shim-callsite/smoke_test.sh` part 4 | pre-check is skipped for non-brief artifacts and for `gt-*` briefs; the three untrusted codes must be dropped before the critic sees them or the loop burns rounds on phantom findings |
| `work` — `skills/work/SKILL.md` | hand-wrote the `gc sling`, then asked the agent to `sleep 5`, grep an assignee, judge "empty after 30-60 seconds", and author `dispatch-provenance.v1` TOML by hand | `replace-with-mctl` (brief-backed path) | `mctl work ready` / `mctl work status` to choose the path; `mctl work dispatch` for path A; `mctl work provenance` to read back | `MCTL-TRACE: <id>` from the dispatch payload | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-6; `tests/lost-bead-filter/smoke_test.sh`; `tests/artifact-root-scoping/smoke_test.sh` | path B (commission of fresh work) stays a raw `gc sling` because `mctl` models no commission path, and keeps both the manual assignee check **and** the hand-written `dispatch-provenance.v1` event bead the lost-bead filter reads; `MCTL_ENABLE_LIVE_DISPATCH=1` must be set or dispatch is a silent dry run; **`mctl` does not scope `artifact_root` per bead** — see the core defect below |
| `immediate-work` — `skills/immediate-work/SKILL.md` | spawned an inline agent for any task, including work with an approved brief behind it — no provenance, no duplicate-dispatch gate | `wrap-with-mctl` | step 0 `mctl work status`; `mctl work dispatch` when brief-backed | `MCTL-TRACE: <id>` when it dispatches | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-6 | a brief-backed task now routes away from in-session execution, which is slower but is the point; `MWRK010` (unadjudicated) is a stop, and immediate-work must not be used to get ahead of it |
| `priority-work` — `skills/priority-work/SKILL.md` | reordered and staffed the queue from a mental model of it, and hand-authored `dispatch-provenance.v1` with `verified_assignee` decided by eye | `wrap-with-mctl` | step 0 `mctl work ready` filter; `mctl work dispatch` + `mctl work provenance` on the brief-backed path | `MCTL-TRACE: <id>` recorded in the dispatch block even on the named-target path | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-6 | named-target dispatch has no `mctl` route and still writes provenance by hand; ranking is per-rig until `--all-rigs` exists |
| `present-briefs` — `skills/present-briefs/SKILL.md` | selected the queue from `stack/.index.jsonl` rows and brief frontmatter only — both cache — so a stale row re-presented a decided brief | `wrap-with-mctl` (read side) | `mctl briefs list --json` once per rig; drop `adjudicated` / `deferred` / `malformed` | read-only; verdict write still goes through the `brief-record-decision` formula | `tests/mctl-shim-callsite/smoke_test.sh` parts 4, 6 | **user-visible:** the queue can now be shorter — briefs whose bead is closed or defer-windowed but whose cache row still says `ready` no longer surface. The verdict write stays on the formula because that formula also rings `brief.decided`, archives the brief, and files the no-brainer-leak event bead, none of which `mctl` models — see "Deferred: the present-briefs verdict write" below |
| `prime-clerk` — `skills/prime-clerk/SKILL.md` | taught `present-briefs → adjudicate-brief → mathcity.work` as prose, with a hardcoded `build-basic-briefed` sling and an eyeballed assignee wait | `wrap-with-mctl` | `mctl briefs list --status pending` for orientation; teaches the three skills as `mctl` wrappers and `mctl trace show` for confirmation | teaches the clerk to keep the `MCTL-TRACE` ids the fork reports | `tests/mctl-shim-callsite/smoke_test.sh` part 4 | the clerk will meet `MBRF004` refusals on most of the live queue; the skill now states that this is expected and is a human decision to resolve |
| `mayor-math` — `skills/mayor-math/SKILL.md` | dispatch doctrine hardcoded `--on build-basic-briefed` for all work | `wrap-with-mctl` | `mctl work ready` for what is dispatchable; defers the dispatch itself to the `mathcity.work` skill | dispatch trace is reported by `mathcity.work` | `tests/mctl-shim-callsite/smoke_test.sh` part 4 | the commission sling is retained verbatim for fresh work; Rules 0-4 (fork-vs-sling, rig-scoped coordinator, convoy, gt HQ fleet) are unaffected |
| `mayor-math-prime` — `skills/mayor-math-prime/SKILL.md` | §5 read `status == "ready"` rows straight out of the legacy `decisions-track/manifest.jsonl` — the inventory #37 demoted and #38 is actively reclassifying | `replace-with-mctl` (§5) / `wrap-with-mctl` (toolkit) | `mctl briefs list --status pending --json` | toolkit teaches `MCTL-TRACE` and `mctl trace show` | `tests/mctl-shim-callsite/smoke_test.sh` part 4 | per-rig until `--all-rigs` exists, so a Mayor priming across rigs must run it per rig and say so; `gt-*` briefs are invisible to it |
| `mayor-math-handoff` — `skills/mayor-math-handoff/SKILL.md` | `city_state` was free prose; in-flight mutations left no handle for the next session | `wrap-with-mctl` | new step 0c: `mctl briefs list --status pending` + `mctl work ready` into a fixed `BRIEFS-PENDING / WORK-READY / HOLDS / IN-FLIGHT-TRACES` block | `IN-FLIGHT-TRACES` carries forward every unconfirmed `MCTL-TRACE` id so the next Mayor can `mctl trace show` it | `tests/mctl-shim-callsite/smoke_test.sh` part 4 | counts are per-rig and exclude `gt-*`; the skill says so rather than presenting one rig's number as the city's |
| `mayor-math-restart` — `skills/mayor-math-restart/SKILL.md` | orientation only: reads the PROMPT, docs, catalog, run-log shard, handoff bead | `no-change` | none — it reads no `BeadStoreAdapter` brief/work state and writes no `BriefCacheAdapter` artifact; its dispatch doctrine is by reference to `mayor-math`, which is wrapped, and the restart PROMPT is generated by `mayor-math-handoff`, which is wrapped | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known — it names no retired command; if `mayor-math` doctrine changes again this file needs no edit, which is the point of the indirection |
| `simple-work` — `skills/simple-work/SKILL.md` | slings `simple-work-briefed` for bounded work and lands a brief on the stack | `no-change` | none — it dispatches a bead that has **no brief yet**, so there is no `BeadStoreAdapter` decision bead for `mctl work dispatch` to address; it is the commission-shaped path, deliberately outside the brief-backed surface | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | its closing instructions still point at `check-briefs` / `present-briefs`, both of which are now mctl-backed, so the hand-off is correct without an edit here |
| `push-the-fleet` — `subdomains/dev/skills/push-the-fleet/SKILL.md` | batch layer over `mathcity.work`; already forbids a raw `gc sling` loop and delegates each item | `no-change` | none in this slice — the register's target was `mctl work batch`, which **does not exist**; the plan's Global Constraints forbid cross-rig mutation until a reviewed batch mode is designed. Its per-item delegation to `mathcity.work` means each dispatch already reaches `mctl work dispatch` through the `BeadStoreAdapter` path | inherited from `mathcity.work` | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | the batch surface remains prose; when `mctl work batch` lands this becomes `replace-with-mctl` |
| `catch-no-brainer` — `skills/catch-no-brainer/SKILL.md` | classifier; emits a JSON verdict line and copies matches into `.pile/.no-brainer/` | `no-change` | none — it is explicitly forbidden from `bd update`/`bd close`/`bd link`, so it never touches `BeadStoreAdapter`; its only writes are into two classifier-owned directories that no `mctl` command reads or reconciles. The register's `mctl briefs classify` was never built | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | its `.no-brainer/` copies are an unreconciled cache; if `mctl briefs classify` is built later this becomes `replace-with-mctl` |
| `decisions-to-briefs` — `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md` | converts pending decisions into brief artifacts and writes decisions-track pointer records | `blocked-by-policy` | none — its output straddles the pile and the legacy decisions-track tree, and `BriefCacheAdapter` owns decisions-track rows as **migration input only**. #38 is actively changing how unknown non-terminal statuses are classified, and the plan holds bulk live decisions-track migration until proof 5 is green and authorized. Rewiring it now would move live records between trees mid-migration | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | re-run this row after #38 lands; the eventual surface is `mctl briefs create` for the pile half |
| `refine-bead-manifest` — `skills/refine-bead-manifest/SKILL.md` | writes `<N>-<slug>-brief.md` files into the legacy decisions-track tree and appends rows to its manifest | `blocked-by-policy` | none — this is a direct `BriefCacheAdapter` write to the legacy decisions-track inventory, which is #38's lane. Routing it to `mctl briefs create` would relocate its output from decisions-track into the pile: a live pipeline change the plan forbids in this slice | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | **this is the largest remaining direct cache write in the skill set.** It is knowingly deferred, not missed; re-run after #38 |
| `file-briefs` — `skills/file-briefs/SKILL.md` | fans out `/brief-prep` per question, then surfaces the batch via `/present-briefs` | `no-change` | none — it composes two skills that are themselves wired, and performs no `BeadStoreAdapter` write and no `BriefCacheAdapter` write of its own (its one pile `ls` is a read) | inherited from `brief-prep` | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | its pile `ls` progress check reads the cache directly; harmless as a progress indicator, wrong as a source of truth |
| `present-it` — `skills/present-it/SKILL.md` | terminal-only context dump; defines the section structure the brief artifacts use | `no-change` | none, **by design** — the register's own post-work audit says "do not route state changes through it". It writes no file and mutates neither adapter; making it a mutation surface would re-create the duplicate control surface this slice removes. Its `BeadStoreAdapter` reads are the caller's | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known |
| `check-brief-policy` — `subdomains/brief-system/skills/check-brief-policy/SKILL.md` | policy checker over brief-system surfaces; declares itself read-only and forbids `bd close`/`bd update` | `no-change` | none — it is explicitly read-only over `BriefCacheAdapter` layout and writes nothing. `mctl briefs doctor` checks canonical-vs-cache invariants, which is a different question from "does this policy document say what it should" | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | its pile/stack path assumptions duplicate `paths.toml`; a future pass could have it read the same resolver |
| `bead-check` — `skills/bead-check/SKILL.md` | read-only bead triage with an explicit allowed/forbidden command table (`bd show`/`list`/`search` allowed; `bd update`/`close`/`gc sling` forbidden) | `no-change` | none — it is read-only over `BeadStoreAdapter` and already respects the canonical bead-first model, which is exactly plan audit rule 3's second clause. It proposes commands for a human to run; it runs none | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | when it proposes a dispatch it should name `mctl work dispatch` rather than a raw sling; cosmetic, and the sling it shows is quoted, not run |
| `check-work` — `skills/check-work/SKILL.md` | work health check | `no-change` | none — read-only over `BeadStoreAdapter`. `mctl work status` answers readiness for **one brief**; this skill answers fleet-shaped questions (stranded, commissioned, waiting) across many beads, which needs the unimplemented `--all-rigs` and a batch status | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | depends on `--all-rigs`; recorded rather than faked with a per-rig loop |
| `check-molecules` — `skills/check-molecules/SKILL.md` | molecule/workflow health inspection | `no-change` | none — read-only over molecule state, which belongs to `gc`, not to either §2 adapter. `mctl` models briefs and brief-backed work, not molecule step graphs, so neither `BeadStoreAdapter` nor `BriefCacheAdapter` covers what this reads | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known |
| `check-build-formulas-and-skills` — `subdomains/dev/skills/check-build-formulas-and-skills/SKILL.md` | validates MathCity-owned formulas and skills | `no-change` | none — it validates files, touching neither `BeadStoreAdapter` nor `BriefCacheAdapter`. The register wanted it to gate `mctl` migration; that gate is now `tests/mctl-shim-callsite/smoke_test.sh` parts 4-9, which is executable rather than a checklist item | n/a | `tests/mctl-shim-callsite/smoke_test.sh` parts 4-9 | the check lives in a test rather than in this skill; deliberate — a grep-based test cannot drift the way a prose checklist can |
| `gate-test-execution-silent` — `skills/gate-test-execution-silent/SKILL.md` | G14 gate; moves failing briefs to `.pile/.rejected/test-execution-silent/` | `no-change` | none — G14 is brief-**quality** gate vocabulary. `mctl` models the adjudication verdict on the `BeadStoreAdapter` bead, not the pipeline gates, and `briefs validate` proves canonical-vs-cache agreement rather than gate satisfaction | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | its rejected-pile move is a `BriefCacheAdapter` write with no canonical counterpart; encoding gate evidence in brief validation stays an open plan item |
| `improve-test-execution-silent` — `skills/improve-test-execution-silent/SKILL.md` | remediation path for G14 failures | `no-change` | none — same boundary as its gate sibling: it repairs gate evidence, which is unmodelled in `BeadStoreAdapter` and outside `BriefCacheAdapter`'s reconciled set | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | pointing its failure messages at `mctl briefs validate` output only becomes useful once validation covers gate evidence |
| `grill-and-present` — `skills/grill-and-present/SKILL.md` | older gated presentation flow, superseded by `create-brief` + `present-it` | `no-change` | none — it is already proposed for retirement and creates no `BeadStoreAdapter` decision bead; wiring a superseded skill to `mctl` would give a retired standard a second life on the new surface, which is the xkcd-927 failure this slice exists to avoid | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | retirement is still unexecuted; it remains reachable |
| `xkcd-927` — `skills/xkcd-927/SKILL.md` | handles duplicate/competing standards; cites `adjudicate-brief` for the reconciling decision | `no-change` | none — its reconciling decision is a **standalone** decision (`bd create -t decision`), not a brief. `mctl briefs create` would manufacture `BriefCacheAdapter` pile artifacts for a decision with no brief pipeline behind it; the canonical `BeadStoreAdapter` store is identical either way | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known — see the same reasoning in `adjudicate-brief`'s standalone half |
| `intercept-bead` — `skills/intercept-bead/SKILL.md` | routes an incoming bead: supersede / duplicate / accept, closing beads that lose | `no-change` | none — it closes **work** beads in `BeadStoreAdapter`, not decision briefs. `mctl briefs adjudicate` closes a `type=decision` bead with a verdict; there is no brief here to adjudicate and no `BriefCacheAdapter` artifact to move | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known |
| `revise-artifact` — `skills/revise-artifact/SKILL.md` | artifact revisor subagent invoked by `coordinate-review` | `no-change` | none — it edits arbitrary artifacts and reaches neither `BeadStoreAdapter` nor `BriefCacheAdapter`. When the artifact is a brief, its parent `coordinate-review` supplies the canonical context | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known |
| `formula-work` — `subdomains/dev/skills/formula-work/SKILL.md` | dispatches formula-authoring work via `gc sling ... --on formula-creator-math` | `no-change` | none — it dispatches a bead with **no decision brief behind it**, so `mctl work dispatch` (which addresses an approved `BeadStoreAdapter` brief) cannot express it; this is the commission-shaped path | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | shares path B's gap with `work`: no mechanical claim verification |
| `audit-recent-work` — `subdomains/dev/skills/audit-recent-work/SKILL.md` | audit report; lists recent pile files by mtime | `no-change` | none — read-only, and its one `BriefCacheAdapter` read is a *recency* question (`ls -lt`) that `mctl` deliberately does not answer: `briefs list` reports canonical `BeadStoreAdapter` state, not filesystem mtimes | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | mtime ordering is cache-derived and can disagree with bead history; acceptable for an audit sweep, not for a queue |
| `hourly-check` — `subdomains/dev/skills/hourly-check/SKILL.md` | hourly city watchdog; counts pile files | `no-change` | none — read-only health reporting. Its pile **count** is a `BriefCacheAdapter` fact (how much is awaiting the shuffle), genuinely different from the `BeadStoreAdapter` pending count; swapping it would silently change what the watchdog watches | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | reporting both counts would be strictly better and is a good follow-up; it needs `--all-rigs` to be city-wide |
| `city-status` — `subdomains/dev/skills/city-status/SKILL.md` | city health report; counts pile files | `no-change` | none — same boundary as `hourly-check`: a `BriefCacheAdapter`-shaped count, reported as such, in a read-only reporting skill | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | same `--all-rigs` dependency |
| `check-zero` — `subdomains/dev/skills/check-zero/SKILL.md` | hallucination gate over draft content | `no-change` | none — it verifies claims in prose and touches neither `BeadStoreAdapter` nor `BriefCacheAdapter` | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | `mayor-math-handoff` step 0 now asks it to verify `bin/mctl --help` alongside `gc --help`; that is a change in the caller, not here |
| `strand-sweep` — `subdomains/dev/skills/strand-sweep/SKILL.md` | sweeps for stranded work; greps bead bodies for dispatch language | `no-change` | none in this slice — the right fix is to read `mctl work provenance`, a typed `BeadStoreAdapter`-backed record, instead of grepping prose for "dispatched\|slung". That is a real improvement **and** a real behavior change to a sweep the fleet depends on, so it is recorded here rather than smuggled into a skills-refactor slice | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | **the strongest deferred candidate in this table.** Its grep heuristic will increasingly disagree with mctl-written provenance as dispatches move onto `mctl work dispatch` |
| `check-labels-and-refs` — `subdomains/latex/skills/check-labels-and-refs/SKILL.md` | LaTeX label/reference checker | `no-change` | none — a LaTeX tool. It entered the pre-implementation grep only via the word "brief" in prose, and touches neither `BeadStoreAdapter` nor `BriefCacheAdapter` | n/a | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | none known — **unrelated**, per the lower-confidence bucket's own triage instruction |
| `math-brief-prep` (formula) — `formulas/math-brief-prep.toml` | fan-out of `brief-prep` per pending source bead, then a single-writer shuffle | `no-change` | none at the formula level — it is a **drain over the `brief-prep` formula**, and the deposit it fans out to is `brief-prep`'s, now `mctl briefs create`. Its own steps write no `BriefCacheAdapter` artifact: the shuffle step explicitly forbids moving briefs to stack or appending index records directly | inherited from `brief-prep` | `tests/mctl-shim-callsite/smoke_test.sh` part 8 | the formula twin `formulas/brief-prep.toml` still describes the old hand-placed deposit; **the SKILL and its formula twin have drifted before (v1.4, gt-vx0g3) and have drifted again here** — reconciling the formula is the top follow-up from this slice |

## Migration notes

### What actually moved

Five skills stopped hand-rolling state transitions:

1. **`adjudicate-brief`** — verdict, cache artifacts, dispatch, and claim
   verification were four hand-rolled steps that could each half-succeed. They
   are now three `mctl` calls, each a checked `EffectPlan` with an `if_status`
   guard, each stamped with a trace id.
2. **`create-brief`** and **`brief-prep`** — both hand-placed the pile file. The
   deposit path was contested three ways in prose; it is now resolved once, by
   `mctl_core/redundant_state.py::artifact_layout`, from `paths.toml`.
3. **`work`** — the sling, the assignee check, and the provenance record are one
   command that fails closed if the bead was never actually claimed.
4. **`present-briefs`** — the presentation queue is still built from cache, but
   it is now filtered against canonical `decision_state`.

### User-facing behavior changes (three, all deliberate)

The rule for this slice was: preserve user-facing behavior **unless** the old
behavior was unsafe *because* it bypassed canonical bead-first state. Three
changes clear that bar, and are recorded here because they are visible:

1. **`present-briefs` can present fewer briefs.** A brief whose bead is closed
   or defer-windowed but whose stack-index row still reads `ready` used to be
   presented; it no longer is. B2.3 ("never re-present an adjudicated brief") is
   a statement about the bead, and the old selector never asked the bead.
2. **`adjudicate-brief` on approve now slings `work-briefed`, not
   `build-basic-briefed`.** `work-briefed` is the router; it selects the formula
   from the live catalog. The old skill hardcoded one formula in prompt text.
   The register's own post-work audit asked for exactly this ("not hand-slung
   formula snippets").
3. **`adjudicate-brief` still syncs the legacy decisions-track manifest, and
   that is deliberate.** The first pass of this slice deleted step 2b as a
   redundant-artifact write. That was wrong, and
   `tests/present-briefs-defer-filter/test_defer_filter.sh` caught it: the test
   extracts and *executes* step 2b's writer to prove a `defer` verdict records
   `defer_until` and a terminal verdict clears it. `mctl` writes neither the
   decisions-track file nor its manifest, so deleting the sync did not hand the
   job to a single owner — it handed it to nobody, re-opening the divergence
   step 2b was written to fix (17 briefs observed diverged on 2026-08-04,
   re-presenting decided decisions). Step 2b is therefore retained as **one
   declared, named exemption**: it runs after the `mctl` write, it touches only
   the decisions-track tree, and `tests/mctl-shim-callsite/smoke_test.sh` part 6
   allows it for this one file, conditional on the block being marked
   `LEGACY-DECISIONS-TRACK`. Retire it when #38 lands.

### Refusals you should expect, and must not route around

`MBRF004` ("Brief bead has no source dependency", B2.1) is an `ERROR`, and
`effects.py::_blocking_preconditions` refuses any mutation whose doctor report
carries one. It fires on **146 of 185** live briefs, including **88 `pending`
and otherwise healthy** ones. **So a refactored skill will legitimately be
refused on most of the live queue today.** That is real current behavior. Every
wired skill now says so, relays the diagnostic verbatim, and stops. The remedy is
a real source link — a human decision — not a bypass.

`MBRF021`, `MBRF004`, and `MBRF005` are the three codes **no skill may branch
on**; `tests/mctl-shim-callsite/smoke_test.sh` part 9 enforces that across every
skill directory. `MBRF021` is a mass false positive (66 of 70 briefs in one rig,
issue #58 / Q5) whose documented remedy would create 66 duplicate artifacts;
`mctl_core/mcp_server.py` already moves it to `untrusted_diagnostics`.
`MBRF004`/`MBRF005` are instrumentation under review: `malformed` means *closed
with no verdict field*, not damaged — the verdicts sit in `close_reason`/`notes`,
which the reader does not consult, and ~39 of the 74 "malformed" beads were never
briefs. See `subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`.

### Core defect found while wiring: `mctl work dispatch` shares one `artifact_root`

`mctl_core/work.py::_formula_invocation` builds the sling with
`artifact_root=<rig-root>/.beads/briefs` — a **shared rig-level** root.
`formulas/work-briefed.toml` documents that var as *"Build or brief artifact
root. For builds, scope per bead (for example `<rig-root>/.gc-builds/<bead>`)"*
and passes it straight through to `build-basic-briefed` on the FULL_CONTINUE
route. So two concurrent FULL_CONTINUE dispatches in one rig share a
stage-artifact root: **the gsp-1bmxuz hazard, re-created inside the typed
command that was meant to remove it.**

This was found because `tests/artifact-root-scoping/smoke_test.sh` failed when
the first pass of this slice deleted the per-bead `build-basic-briefed` examples
from four skills, on the (wrong) grounds that `mctl` now scoped the root itself.
It does not. The examples were restored, the false claim was removed from every
skill that carried it, and each wired skill now states the gap and says to
serialize approvals on one rig rather than re-slinging by hand.

**Fixing it is a `mctl_core` change, not a skill change**, and it is out of
Slice 7's scope. It is the highest-value follow-up in this document.

### Known gaps, recorded rather than worked around

- **`gt-*` beads are unreachable through `mctl`.** The city-root HQ store is not
  a registered rig in `city.toml`, so `--rig gt` fails with
  `MCTL_CONTEXT_UNKNOWN_RIG`. `check-briefs` keeps a direct `bd` fallback (whose
  `^Status:` parse is separately broken against `bd` 1.1.0);
  `adjudicate-brief` escalates instead of improvising a second write path;
  `present-briefs` leaves `gt-*` candidates in the queue on the cache filters.
  Every wired skill states the gap rather than pretending the rig resolves.
- **`--all-rigs` was specified in Slice 2 and is not implemented.** Another agent
  is adding it to the core. **No skill in this slice builds its own cross-rig
  loop** — `mayor-math-prime`, `mayor-math-handoff`, `priority-work`,
  `check-work`, `hourly-check`, and `city-status` all make the single-rig call
  and name the dependency.
- **`mctl work batch` does not exist**, which is why `push-the-fleet` is
  `no-change`. Cross-rig mutation is forbidden by the plan's Global Constraints
  until a command-specific batch mode is designed and reviewed.

### Deferred: the `present-briefs` verdict write

The register's expected disposition was to replace `present-briefs` Phase 4 with
a typed verdict command. It was **not** done, and the reason is concrete rather
than cautious: `formulas/brief-record-decision.toml` performs three effects
`mctl` does not model —

1. it rings `brief.decided`, which wakes the `post-decision-file-or-sendback`
   order;
2. it archives the decided brief and its staging directory under `archive/<slug>/`;
3. on a no-brainer leak it writes a durable `no_brainer_leak` event bead plus its
   replay cache.

`mctl briefs adjudicate` writes the bead, the decision TOML, and the stack index
row — a strict subset. Routing the verdict through `mctl` *and* the formula would
double-write the decision record (keyed `<brief_id>.toml` versus
`<brief_slug>.toml`, which are not even the same key); routing it through `mctl`
*only* would silently drop the bell and the archive. Both are worse than leaving
the write where it is. The read side was wired instead, and the right fix is to
model the bell / archive / leak edges in `mctl_core` — a core change, not a skill
change.

### Follow-ups this slice deliberately did not take

| Item | Why it was left | Unblocked by |
| --- | --- | --- |
| `refine-bead-manifest` decisions-track writes | live legacy-inventory writes mid-migration | #38 fail-closed classifier + proof 5 |
| `decisions-to-briefs` rewiring | same | #38 |
| `strand-sweep` reading `mctl work provenance` instead of grepping prose | changes a sweep the fleet depends on | its own brief |
| `push-the-fleet` batch dispatch | `mctl work batch` unbuilt; cross-rig mutation forbidden | a reviewed batch-mode design |
| `formulas/brief-prep.toml` deposit step | the formula twin still describes the hand-placed pile write the SKILL just stopped doing | this slice — **the drift is live now** |
| `present-briefs` verdict write | `brief.decided` / archive / leak-event edges unmodelled | a core change to `mctl_core` |
| `hourly-check` / `city-status` reporting both counts | needs `--all-rigs` for a city-wide number | Slice 2's `--all-rigs` |
| **`mctl work dispatch` per-bead `artifact_root`** | core defect found while wiring; recreates gsp-1bmxuz inside the typed command | a `mctl_core/work.py` fix — **highest-value follow-up here** |
| `adjudicate-brief` step 2b (legacy decisions-track sync) | `mctl` models neither the file nor the manifest; deleting it re-opens #18 | #38 |
