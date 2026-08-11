# mathcity

**Gas City mathematical work pack.** Codifies the brief pipeline — formulas, orders, gate policy, and skills — that routes math research decisions (branches, PRs, experiments) from artifact to adjudication.

## Links

- Gas City platform: https://github.com/gastownhall/gascity
- Beads issue tracker docs: https://gastownhall.github.io/beads/
- **Installation & user guide (start here):** [docs/INSTALL.md](./docs/INSTALL.md)

---

## What is the brief system

The brief system is a structured decision pipeline for math research work. When an agent completes a branch, closes a bead, or proposes an experiment, it does not automatically merge or act. Instead it produces a brief — a formatted document that describes the artifact, the work done, the gate evidence, and a clear statement of what decision is needed. Briefs are the unit of work that flows between automated agents and human user.

The pipeline has two main phases. In the production phase, `brief-prep` (a skill that composes `grill-and-present`, `coordinate-review`, and the gate runner) prepares the brief from the source artifact, runs all required gates, and deposits the result into the `.pile` at `~/.gc/mathcity/briefs/.pile/`. The `brief-shuffle-pile` order fires on condition, picks up pile items one at a time, applies gate-keep rules, and either promotes each brief to the `~/.gc/mathcity/briefs/stack/` with a manifest entry or rejects it to `.pile/.rejected/`.

In the adjudication phase, the outside clerk (or Mayor) runs the `present-briefs` skill to drain the stack and present briefs to human — presentation is human-facing and cannot be staffed by a gc order. No-brainer-classified briefs are collapsed into a single one-line block; full briefs are rendered through `grill-and-present`. human adjudicates — approve, reject, defer, or revise. The `adjudicate-brief` skill records the verdict ON the brief bead itself (the brief bead is `type=decision` — one-bead model) and closes it; no separate decision bead is created. It rings the `brief.decided` event, which fires the machine cascade on the `mathcity.brief-operator` pool: two event-driven orders fire — `brief-decision-dispatch` acts on the decision (reassigns to `gc.publisher` — the rig's merge-queue agent, informally "refinery" — on approve; creates a follow-up bead on reject/revise; marks defer with no action), and `post-decision-file-or-sendback` routes the brief itself to either a successor re-briefing or archive. The `brief-archive-sweep` cooldown order handles residual cleanup.

### Pipeline diagram

```
source bead closes (needs-decision label)
        │
        ▼  on-merge-brief-record order (event: bead.closed, rig-scoped)
        │  → creates brief-record bead, enters brief-prep pipeline
        ▼  brief-prep formula (or math-brief-prep for fan-out)
        │  → gates checked (brief-gate-keep), brief.md deposited in .beads/briefs/.pile/<slug>/
        ▼  brief-shuffle-pile order (condition-trigger, rig-scoped)
        │  → single-writer: promotes .pile → .beads/briefs/stack/
        ▼  /present-briefs skill (CLERK-DRIVEN — cannot be an order)
        │  → no-brainers: compact one-line block; full briefs: grill-and-present
        ▼  /adjudicate-brief skill
        │  → brief-record-decision formula: writes decision, emits brief.decided
        ├── brief-decision-dispatch order (event: brief.decided, city-scoped)
        │   approve  → reassign source bead to <rig>/gc.publisher ("refinery")
        │   reject   → create follow-up bead with reason
        │   revise   → create follow-up bead with feedback
        │   defer    → mark dispatched, no action
        └── post-decision-file-or-sendback order (event: brief.decided, city-scoped)
            FILE     → fire brief-prep for successor bead
            SEND-BACK → request archive → brief-archive-on-request order catches it
```

---

## Filter System

The filter system is the repeat-pattern layer around the brief and bead
workflows. It classifies mechanical cases, records evidence, and routes the
next decision to a brief or repair workflow. Filters do not silently merge,
close, defer, or override human-only decisions.

Start with the [filter user manual](./docs/filters/README.md). The four current
filter documents are:

- [Repair no-brainer and gates](./docs/filters/repair-no-brainer-and-gates.md)
- [Formula repair feedback](./docs/filters/formula-repair-feedback.md)
- [Bead repair no-brainer and gates](./docs/filters/bead-repair-no-brainer-and-gates.md)
- [Bead repair feedback](./docs/filters/bead-repair-feedback.md)

The user-facing entry points are the existing skills: `brief-prep`,
`catch-no-brainer`, `present-briefs`, `adjudicate-brief`, and `bead-check`.
The manual also names the formula-level invocations used for producer-failure
and lost-bead rollups.

---

## The Work / Brief Graph (two-layer model)

Conceptual overview (P5.4 non-normative); the cited source files are authoritative.

The city's work is a directed graph with two coupled layers. The **brief layer** is the decision plumbing (deciding what to do). The **work-execution layer** is where beads actually get worked (doing it). They are joined not by a single bridge but by a small bundle of asymmetric, multi-edge couplings.

```
  BRIEF LAYER (decision plumbing)
  source-closed-nd ─▶ brief-record ─▶ pile ─▶ stack ─▶ decided ─▶ { publisher | followup | archived }
        ▲                                                   │
        │  work→brief: label-on-close (1 edge)              │  brief→work: 4 verdict edges
        │  on-merge-brief-record on bead.closed             │  approve / reject / revise / defer
        │  (acts only if `needs-decision`)                  ▼
  ══════╪═══════════════════════════════════════════════════════════════════════
  WORK-EXECUTION LAYER (two substrates)                     │
    core mol-*  (flat, no lifecycle)  ◀──────────────────── approve → <rig>/gc.publisher
      • mol-do-work      : edit cwd, commit in place, close                (publish phase only)
      • mol-polecat-commit: worktree on base_branch, DIRECT commit+push,   reject  → fresh [rejected] bead
                            NO feature branch, NO merge                    revise  → fresh [revise] bead
    gascity build-basic (full factory)                                    defer   → no-op
      requirements → plan → plan-review → decompose →
      implement (FAN-OUT to N gc.implementation-worker, each in a
      detached-HEAD worktree at <rig>/worktrees/<anchor-id>) →
      FAN-IN (summarize) → review → finalize → publish
```

### Work-execution layer — two substrates

- **core `mol-*`** — compiled into the `gc` binary under `gascity/internal/bootstrap/packs/core/formulas/`. Flat, no lifecycle. `mol-do-work` edits in cwd, commits in place, and closes (`mol-do-work.toml`); `mol-polecat-commit` runs a worktree on `base_branch` and does a **direct commit + push to `base_branch` — NO feature branch, NO merge** (`mol-polecat-commit.toml:1-16`).
- **gascity `build-basic`** — the full factory (`gascity/formulas/build-basic.formula.toml`): requirements → plan → plan-review → decompose → **implement (convoy FAN-OUT to N `gc.implementation-worker`, each in a detached-HEAD worktree at `<rig>/worktrees/<anchor-id>`)** → FAN-IN (summarize) → review → finalize → publish. Entry-point table at `gascity/README.md:73-81`; the launcher rig root is never mutated (`assets/workflows/do-work/prepare-worktree.md:20-28`, `implement.md:19-29`).
- **mathcity `build-basic-briefed`** (Mechanism D2) — `extends = ["build-basic"]` and redeclares the terminal `publish` step in-place (formula-compiler `mergeSteps` replaces same-id steps at the same position), so the factory ends by **producing a decision brief** (brief-prep SKILL + catch-no-brainer) instead of pushing/PR-ing. The `gc.publisher` AGENT is untouched — no brief→publish cycle; shipping happens on APPROVE via the `brief-decision-dispatch` verdict edge below (`mathcity/formulas/build-basic-briefed.formula.toml`, asset `mathcity/assets/workflows/build-basic-briefed/publish.md`).

### The critical truth

**Nothing in gascity or core ever merges to main.** `publish` only pushes a branch / opens a PR and is **no-op by default** (`push`/`open_pr` = false) — `publish.formula.toml:19-45`, `build-basic/publish.md:1-11`, `REQUIREMENTS.md:145,779`. The "refinery merges branch to main" concept was a **gastown-pack vestige, removed 2026-07-09 (`ba2ff381`)**. `MergeQueuePolicy` defaults to `observe` (`github_pr_monitor.go:12,55-67`).

### The coupling (multi-edge, asymmetric — not one bridge)

- **work → brief** — a single label-on-close edge. `on-merge-brief-record` fires on `bead.closed` and acts only if the closed bead carries the `needs-decision` label (`mathcity/orders/on-merge-brief-record.toml`). Because it keys on the close event, it attaches at ANY terminus (close-source-anchor, `finalize`, `mol-do-work` close) — briefs enter at different phases by *when you close + label*, not via a phase-pinned hook. A manual mid-lifecycle path also exists: sling `brief-prep` against any bead at any time.
- **brief → work** — four verdict edges from `brief-decision-dispatch` (`mathcity/formulas/brief-decision-dispatch.toml`): **approve** reassigns the source bead to `<rig>/gc.publisher` (publish phase only) (direct-commit beads with no `branch` metadata: decision is recorded and settled, no publisher handoff); **reject** files a fresh `[rejected]` bead; **revise** files a fresh `[revise]` bead; **defer** is a no-op. (FILE via `file-or-sendback-route` loops back *into the brief layer*, not into work.)

### Direct-commit approve behavior (gt-yv8p2)

The approve path uses a fail-closed three-state branch check: an approve of a direct-commit bead (`mol-do-work` / `mol-polecat-commit` — work is already on the default branch, no feature branch) where `gc bd show` succeeds and returns no `branch` metadata records the decision as a SUCCESS ledger line and settles with no publisher handoff; an approve with `branch` metadata present keeps the full publisher handoff path; a `gc bd show` error is retried (fail-closed — a transient error never silently settles as "no branch"). Fix tracked: gt-yv8p2.

### Cycle basis (brief layer)

The brief layer's cycle space has dimension β₁ = |E| − |V| + C = 18 − 12 + 1, minus the dropped intake-consistency artifact → **6 fundamental loops**. A basis:

- **B1** — merge/publish re-enters (now: approve → publisher → push/PR, NOT a merge).
- **B2** — revise/reject follow-up.
- **B3** — FILE re-prep.
- **B4** — two routes to archive.
- **B5** — no-brainer auto-execute.
- **B6** — shuffle-reject sweep.

Plus terminating (acyclic) paths: approve → publish when non-reentrant, and the decided → archived sink; defer is a no-op. Note that "enumerate every cycle" is ill-posed; the correct check is that this basis **spans** the cycle space, not that it lists all cycles.

---

## Skill canonicality

**The mathematics pack is the single source of truth for all brief-pipeline and math-workflow skills.**

- `skills/<name>/SKILL.md` is the canonical file for parent-pack skills.
- `subdomains/*/skills/<name>/SKILL.md` is the canonical file for subdomain skills.
- Plain-session skill exposure should materialize from the canonical pack file
  into the consuming agent's configured skill directory. Never edit the
  materialized copy as the source of truth.
- **Edits always land as commits to this repository.** Local mirrors or
  symlink sinks must point back to the canonical pack files.
- **New brief-pipeline or math skills are created inside
  `skills/<name>/` first**, then exposed through the consuming
  environment's configured skill materialization path.
- Run the local skill-exposure checker for your environment to verify every
  materialized skill resolves and every skill directory contains `SKILL.md`.

Skills currently managed under this policy:
`brief-prep`, `catch-no-brainer`, `coordinate-review`, `critical-review`,
`formula-creator`, `grill-and-present`, `is-good-experiment`, `is-good-test`,
`present-briefs`, `present-it`, `adjudicate-brief`.

---

## Skills

> **Complete index:** for the single cross-pack table of **all** mathcity skills (parent + every subdomain), see **[README-skills.md](./README-skills.md)** — the canonical index. The table below is the parent-pack local view.

These skills ship with the parent pack (subdomain child packs carry their own — see `subdomains/*/README.md`). They are bare `SKILL.md` composition units — no wrapper scripts. The `grill-with-docs` and its derivatives are based off [Matt Popocock's Skills](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs). Most of the skill formulas and plans were developed using a ``fixed point finder'' where artifacts (in this case the skill) goes through a comprehensive review until the agents converge on the skill. (The fixed point finder is now deprecated in favor of the gascity native version.)

| Skill | Description |
|---|---|
| `brief-prep` | End-to-end brief production: turns an artifact (branch, bead, PR, diff) into a stack-eligible brief with all gates satisfied and bookkeeping recorded. Branches on no-brainer classification to compact or full-form output. |
| `catch-no-brainer` | Classifies a brief against the 5-criterion no-brainer test and signals compact-form eligibility to downstream consumers. Records candidates; never auto-merges or closes beads. |
| `coordinate-review` | Iterative create/review loop: spawns `critical-review` and `revise-artifact` subagents in alternation until an artifact converges to approved state under the META-FP formula. |
| `critical-review` | Adversarial reviewer for any artifact (SKILL.md, plan, theorem, LaTeX, code). Produces a structured APPROVING or NEEDS-REVISION verdict with prioritized action items. |
| `grill-and-present` | Produces decision-ready briefs by gathering all 10 present-it sections, grilling on ambiguity, running tests, and FP-converging the brief through `critical-review` before presenting. |
| `is-good-experiment` | Pre-flight check for experiment proposals. Decides whether a computation or research probe is well-designed before any compute is spent running it. |
| `is-good-test` | Thin specialization of `is-good-experiment` for test files. Evaluates whether a test's design answers "does X work?" meaningfully. |
| `present-it` | Produces a decision-ready brief on a code artifact. Enforces the Decision-at-Top invariant. Supports full-form and compact form outputs. |
| `adjudicate-brief` | Records standalone human adjudications and policy locks using `bd create -t decision` (renamed from `record-decision`). Refuses non-canonical stores. Brief verdicts are the exception: they are recorded ON the brief bead itself (one-bead model), never as a second bead. |
| `present-briefs` | Batch-presents N briefs in parallel and keeps a hot queue (≥2 pre-presented) with auto-backfill on each decision. |
| `prime-clerk` | Primes the outside clerk for the adjudication phase: orients it on the `present-briefs` → `adjudicate-brief` flow (drain the stack, present each brief to the human adjudicator, record the verdict on the brief bead) so a fresh clerk session can run the loop without prior context. |
| `create-brief` | Produces the durable, gated `.md` brief artifact for the brief stack — the file-artifact sibling of `present-it`. |
| `create-artifact` | Creator half of the review loop: produces a new artifact from a spec (dispatched by `coordinate-review` or directly). |
| `revise-artifact` | Applies a list of action items (typically from `critical-review`) to an artifact and outputs the revised version. |
| `compare-artifacts` | Semantic diff between two text artifacts: similarity score + token-overlap signal for "are these effectively the same?" |
| `fp-finder-skill` | Fixed-point convergence engine for SKILL.md files: every accepted revision must be strictly shorter AND still APPROVING. |
| `formula-creator` | Creates a formula TOML in a Gas City pack and validates the gc/bd command surface before committing. |
| `create-convoy` | Creates a properly configured OWNED convoy for an epic bead — the fan-out container for one WIP-dispatcher slot. |
| `fan-out` | Fans an epic bead out into convoy sub-beads without consuming extra WIP-dispatcher slots; companion of `create-convoy`. |
| `immediate-work` | In-session synchronous dispatch: spawn the right agent NOW for a specific bead or task (no pool, no queue). |
| `priority-work` | Async targeted dispatch: bump a bead to P0 and dispatch it to a NAMED agent immediately, bypassing queue order. |
| `mayor-math` | Supplements `gc.mayor` with rig-scoped sling mechanics for the mathcity workflow. |
| `mayor-math-restart` | Full Mayor session orientation; restart context auto-injected via PreToolUse hook before the skill fires. Run at the start of every new Mayor session. |
| `authorize-git-operation` | Human-authorization gate for irreversible git operations (push, merge, PR, delete, release); records the verdict as a decision bead. |
| `remember-this` | Routes a mid-session insight to the right durable store (`bd remember`, decision bead, MEMORY.md pointer). |
| `gc-recycle-bead` | Graceful lifecycle transitions for research beads: ABSORB (merge unique content into canonical bead, close with `absorbed_by` metadata), ARCHIVE (add `archived-research` label + defer to prevent dispatch), MATERIALIZE (write key content to versioned file). |
| `bead-check` | Read-only diagnostic: judge one bead against all current policies and emit a disposition recommendation (propose-only front-end for `gc-recycle-bead` / `intercept-bead` / `handoff-bead` / dispatch). |
| `prime-outsider` | Primes an outside (non-gascity) agent after compaction or a new session: finds beads + handoff, restates standing rules. |
| `repo-to-city` | Reference map from repository names to city-side rig, repo-side working copy, and beads prefix. |
| `dolt-init` | Initializes the bd Dolt database and sets the dolt remote in both the city-side rig and repo-side working copy (HALTs unless the remote is named `<repo>-dolt`). |
| `dolt-pull` / `dolt-push` | Pull/push the bead database against its private `-dolt` remote (data plane; bans force-push). |
| `get-best-apis` | Fetches live LLM benchmark rankings + current API pricing across vendors and renders a comparison table. |
| `get-best-models` | Recommends the best open-weights/local LLM for a hardware constraint and use case. |
| `gate-test-execution-silent` | G14 gate — pure PASS/FAIL check: verifies that a brief carries a non-silent test-execution tri-state declaration (`test-execution: PASSED/NOT APPLICABLE/REQUIRED`) and, when PASSED is claimed, that §5 contains command + exit code + wall time evidence. Auto-throwback gate; no human adjudication. |
| `improve-test-execution-silent` | G14 improve step — auto-repair companion to `gate-test-execution-silent`. Adds `test-execution: REQUIRED — not yet run` when the brief is silent (Case A); emits ESCALATE when evidence is incomplete (Case B). Identity on passing input. |

---

## Formulas

Formulas are the executable units the order system pours. Each is a `.toml` in `formulas/`.

| Formula | What it does |
|---|---|
| `brief-archive-sweep` | Sweeps old rejected and decided brief artifacts into archive state via deterministic file moves. Runs as phase=vapor (no LLM turn per step). |
| `brief-decision-dispatch` | For each undispatched decision record, executes the routing action: reassign source bead on approve, create follow-up bead on reject/revise, mark-only on defer. |
| `brief-gate-keep` | Runs the gate registry against one brief. Mechanical gates checked by scripts; judgment gates as explicit work steps; stop/manual gates fail closed unless evidence records human authorization. |
| `brief-prep` | Producer side of the brief-bundle workflow. Turns a bead, artifact, or user request into a staged brief with gate evidence attached, then submits to the pile. |
| `math-brief-prep` | Fan-out variant of `brief-prep`: spawns one `brief-prep` instance per pending source bead (drain), then runs single-writer shuffle after the fan-in. |
| `brief-present-next` | Drains all pending stack briefs in one session. No-brainers are collapsed into one-line items; full briefs are rendered via `grill-and-present`. |
| `brief-record-decision` | Records human's verdict on the presented brief's bead itself (one-bead model), closes it, and archives the run. |
| `brief-shuffle` | Single-writer shuffler: processes at most one pile item per run, applies gate-keep, and either promotes to stack (with manifest append) or rejects to `.pile/.rejected/`. |
| `brief-watchdog-refill` | Monitors the brief stack; when below target, identifies ready source work and opens or routes brief-prep work. Does not fabricate briefs. |
| `codex-dispatch` | Dispatches a task to the codex-worker for cross-model critical review, creative design, or large-plan analysis. Never fired by automated orders — pour explicitly only. |
| `file-or-sendback-route` | Post-decision gate: logs the routing choice for a decided brief and fires downstream work — FILE (re-brief a successor) vs SEND-BACK (archive). Never reassigns or merges. |
| `no-brainer-classify` | Classifies no-brainer candidates and records results. Shortcut execution (`guarded-execute` step) is activated when `no-brainer-process.toml` runs with `mode = "guarded-execute"`. **Mode fix applied 2026-07-14 (gt-d3h6e)** — auto-execution fires once the controller starts. |
| `on-merge-brief-record` | Inspects recently closed beads; for those carrying the `needs-decision` label, creates a brief-record bead and enters the brief-prep pipeline. |
| `brief-review-patrol` | Backstop for briefs stuck at `review_gate: pending`. Advances them through Phase 5 or escalates. Rig-scoped, cooldown 30m, pool: `gc.run-operator`. |
| `decision-enforce` | Enforces the bd-decision-canonical principle: checks that a decision record exists and that verdict/bead alignment is consistent. |
| `test-execution-request` | Formal request workflow for test execution that carries risk or cost and should not happen silently. |
| `upf-experiment-dispatch` | Dispatches and breadcrumbs an experiment that belongs on UPF (the compute rig). |

---

## PR Pipeline

The `pr-pipeline` pack is a separate Gas City pack that ships six formulas for
the author-side PR workflow. When imported into a city, they are accessible via
`gc sling` or the command surface below. Mathcity's own `pr-pipeline-briefed`
formula wraps that workflow at the decision-brief boundary; it does not vendor
or override the upstream `pr-pipeline` pack.

| Formula | Command | Purpose |
|---------|---------|---------|
| `mol-pr-start` | `gc pr-pipeline pr plan <issue>` | Issue → structured plan (no code written) |
| `mol-pr-blast-radius` | `gc pr-pipeline pr blast-radius "<scope>"` | Map impact surface of a proposed change |
| `mol-pr-review` | `gc pr-pipeline pr review <pr>` | 11-category outgoing-PR self-review scorecard |
| `mol-pr-ship` | `gc pr-pipeline pr ship` | Pre-push gate: simplify → review → checks → readiness report |
| `mol-pr-triage` | (sling directly) | Scan/classify open upstream issues into ranked work queue |
| `mol-pr-from-issue` | `gc sling <rig>/gc.run-operator mol-pr-from-issue --formula --var issue_number=<N>` | Macro chain: issue → branch-ready PR |

`mol-pr-from-issue` is the full author-side macro. It does **not** push or open a PR by default (`auto_push=false`). Add `--var auto_push=true` only with explicit authorization.

> **Note on "pr-pipeline":** this refers to the external **pack**, not a git
> branch. Mathcity should compose with that pack instead of carrying a private
> fork of its formulas.

---

## Development And Tests

Mathcity has focused executable coverage for the brief-system watchdogs and
shell smoke coverage for formula wiring. The current Python unit coverage lives
in two files:

- `tests/stuck-bead-watch/test_stuck_bead_watch.py` — pure tests for routed
  bead detection, live/dead assignee handling, priority grace windows, cache
  round-trips, linked event creation, schema-valid lost-bead classifications,
  and idempotent escalation.
- `tests/tail-end-detector/test_tail_end_detector.py` — pure tests for
  ready-but-never-dispatched tail detection, idle-age measurement, filtering
  of scaffolding/non-work/gated/routed beads, oldest-first ordering, and
  supersession heuristics from parent, relation, and near-duplicate signals.

Run the focused Python suite from the pack root:

```sh
python3 -m pytest \
  tests/stuck-bead-watch/test_stuck_bead_watch.py \
  tests/tail-end-detector/test_tail_end_detector.py
```

Smoke tests live under `tests/*/smoke_test.sh` and exercise formula/skill
surfaces that are easier to check through shell fixtures than through Python
unit tests.

Performance work should use explicit profiling evidence. For Magma package
work, use `profile-magma` to create a `probe-profile-<topic>.mag` harness and
record the before/after profile evidence in the bead or brief. LLM/model
selection benchmarks are handled by `get-best-apis` and `get-best-models`;
record the date and source of any benchmark data because those rankings and
prices change over time.

---

## Orders

Orders wire formulas to triggers.

| Order | Trigger | Description |
|---|---|---|
| `brief-archive-on-request` | event (`brief.archive_requested`) | Archives a sent-back brief immediately when routing requests it, without waiting for the 24h sweep. |
| `brief-archive-sweep` | cooldown 24h | Archives decided and rejected brief artifacts without deleting decision records. |
| `brief-decision-dispatch` | event (`brief.decided`) | Acts on verdict: approve → reassign source bead to `<rig>/gc.publisher` (merge-queue agent, "refinery"); reject/revise → create follow-up bead; defer → no-op. Pool: `mathcity.brief-operator`. |
| ~~`brief-present-next`~~ | ~~manual~~ | **RETIRED 2026-07-13 (P4.2 migration).** A gc order can never staff a human presenter (its `mayor` pool never resolved). Presentation is now the outside clerk's `present-briefs` skill. The `brief-present-next` FORMULA is kept; only the order was removed. |
| `brief-shuffle-pile` | condition | Fires whenever `~/.gc/mathcity/briefs/.pile/` contains at least one `.md` file. Promotes or rejects one brief per run. Pool (city/rig="" instance): `mathcity.brief-operator`. |
| `brief-watchdog-refill` | cooldown 30m | Checks whether the brief stack needs refill work and routes brief-prep tasks. |
| `brief-watchdog-refill-on-stack-low` | event (`brief.stack-low`) | Immediate refill trigger on stack-low event. Event emitted by `assets/scripts/brief-stack-low.sh --emit` (post-decision hook); script measures 3 signals (approved ≤ threshold, total ≤ threshold, unlock_pos ≤ threshold). |
| `brief-review-patrol` | cooldown 30m | Backstop for briefs stuck at `review_gate: pending`. Advances or escalates. Rig-scoped, pool: `mathcity.brief-operator`. |
| `no-brainer-process` | manual | Classifies and auto-executes no-brainer candidates. Mode fix applied 2026-07-14 (gt-d3h6e): `[vars] mode = "guarded-execute"` now set; auto-execution fires once controller starts. Kill-switch: absent `auto_merge_enabled` = ON. |
| `on-merge-brief-record` | event (`bead.closed`) | Files a brief-record after the refinery closes a bead carrying `needs-decision`. Rig-scoped because work beads are rig-local. |
| `post-decision-file-or-sendback` | event (`brief.decided`) | Routes the decided brief: FILE (re-brief a successor bead) or SEND-BACK (archive). Never reassigns or merges. |
| `stuck-bead-watch` | cooldown 90s | Detects routed beads (`gc.routed_to` metadata set, incl. formula/order-internal step beads) that never made progress; after a priority-scaled grace window (P0=5m/P1=10m/P2=20m/P3-4=45m), feeds them into the `lost-bead-classification-rollup` pipeline above via a linked `type=event` bead. Runs `exec` (pure Python, no LLM/pool-session cost per tick). Named workaround (P1.17) for a missing gascity-core per-dispatch liveness hook — see `gt-c4g63`. |

---

## Rig wiring — how mathcity reaches every rig

How the rig-scoped orders above (and the pack's agents/formulas) get bound
per rig. Source of truth (P5.4): gascity `internal/config/pack.go` at
commits `8f7947af` (defaults expansion) and `17f066839` (fan-out exclusion);
verified live 2026-07-15 — `gc order list` shows `on-merge-brief-record`
bound for the HQ instance (`rig="-"`) **plus one instance per rig**, and the
per-rig instances fire order-run beads tagged
`order:on-merge-brief-record:rig:<rig>`.

**Mechanism.** mathcity is declared in two places in the consuming city, serving
two scopes:

- consuming `city.toml` `[defaults.rig.imports.mathcity]` — composed as a base
  layer under **every rig's** import table at composition time
  (`expandPacks`). A rig that authors its own `[rigs.imports.mathcity]`
  wins wholesale; the merge is composition-only (`rig.Imports` is never
  rewritten), so `gc config` rewrites never persist the injected defaults.
- consuming city root `pack.toml` `[imports.mathcity]` — the **HQ
  (city-scope)** instance:
  brief-pipeline orders/formulas at `rig=""`. Child rigs do NOT get their
  binding from this entry: the per-rig fan-out of city imports skips any
  binding covered by `[defaults.rig.imports]` (invariant: an import binding
  composes into a rig at most once; precedence rig-authored > city defaults
  > city-import fan-out — gascity `17f066839`, bead gs-lmf).

**Rig onboarding.** New rigs need no mathcity wiring: `gc rig add` creates
the rig and the defaults cover it at the next composition — no re-import
pass, no per-rig `[rigs.imports]` block. (Pre-existing rigs were proven
covered at deployment: all 15 rigs bound with zero per-rig edits.
`gc rig add` additionally materializes the defaults into the new rig's
authored imports — a redundancy tracked upstream as gs-nc5; harmless, the
authored copy simply wins.)

**Per-rig off-switch.** To disable one of these orders on one rig without
touching the pack, use an order override in the consuming city's `city.toml` (via a pack
update per P1.2, never a hand-edit):

```toml
[[orders.overrides]]
name = "on-merge-brief-record"
rig = "<rig-name>"
enabled = false
```

## Agents

### codex-worker

Located at `agents/codex-worker/agent.toml`. A simple Codex worker scoped to the rig, using the `codex` provider with `fallback = true` and `permission_mode = "no-approval-sandboxed"`. It is the execution target for `codex-dispatch` pours — used when an independent cross-model perspective is needed on a design decision, a prior agent attempt has failed, or a large-plan analysis warrants a second opinion before committing. It is never fired automatically; all dispatches are explicit. Operators who need broader filesystem or network access must configure that locally outside the shipped pack.

### brief-operator

Located at `agents/brief-operator/agent.toml`. A pack-local, **city-scope** operator that runs the deterministic brief-pipeline FORMULA steps — shuffle bookkeeping, watchdog-refill measurement, decision dispatch, file-or-sendback routing, archive sweeps, and no-brainer classification. It is **persistent** (`min_active_sessions = 1`, `max_active_sessions = 12`) so brief-pipeline orders staff deterministically without relying on on_demand dispatch (open bug gs-7mr). The brief-pipeline orders reference it by the explicit binding-qualified pool `mathcity.brief-operator`. It **never adjudicates or presents a brief** — presentation is the outside clerk's job (`present-briefs`), and adjudication belongs to the human operator.

---

## 16-Gate system

Every brief is evaluated against a registry of 16 gates before it can be promoted from the pile to the stack. This system was made autonomously after initially recieving many reviews. As the user approved decisions one has to classify them as "no-brainers". Every 10 new "no-brainers" sparks a review of the gate process so that the no-brainer reviews are caught and immediately processed. This allows us to cut down on the number of briefs we have to read. 

Gates have developed into four kinds (so far):

- **mechanical** — checked deterministically by script; no judgment required.
- **review** — requires an agent or human reviewer to evaluate evidence.
- **stop** — fails closed unconditionally unless explicit human authorization is recorded in the evidence.
- **manual** — requires a human outcome or explicit N/A.

`fail_closed = true` is set at the registry level, meaning any missing or failing gate blocks promotion.

| Gate | Name | Kind | Brief description |
|---|---|---|---|
| G1 | test-evidence | mechanical | Test claims must include exact command, scope, result, and date — or explicit N/A with surface-check evidence. |
| G2 | good-test | review | A reviewer must judge whether the test evidence meaningfully tests the claimed behavior. |
| G3 | shell-scripts-testable | mechanical | Shell-script changes must name runnable validation or state why no script surface is touched. |
| G4 | critical-review | review | A critical-review pass must look for correctness risks, policy misses, and missing evidence. |
| G5 | server-touching-exclusion | stop | Server-touching work cannot pass the shortcut path without explicit human authorization. |
| G5b | user-skill-touching-exclusion | stop | User skill changes cannot pass shortcut automation without explicit human authorization. |
| G6 | latex-gate | manual | LaTeX-bearing work needs the LaTeX gate outcome or an explicit no-LaTeX surface check. |
| G7 | artifacts-staging | mechanical | Artifacts must be staged under the brief run directory and referenced from the brief. |
| G8 | brief-record-bookkeeping | mechanical | Pile, stack, manifest, brief bead `type=decision`, and recorded-verdict/archive records must remain consistent. |
| G9 | no-brainer-filter | review | Shortcut classification must be explicit and cannot override stop gates or human-only decisions. |
| G10 | improve-readme | mechanical | Each qualifying iteration must show the README improvement or explain why no README surface exists. |
| G11 | breadcrumb | mechanical | Experiment or deferred work must leave a durable breadcrumb to the source, artifacts, and next owner. |
| G12 | auto-merge-kill-switch | stop | Automation checks the two-level N5 kill-switch hierarchy (city `<city-root>/.beads/auto_merge_enabled`, then rig `<rig-root>/.beads/auto_merge_enabled`) before executing; a switch that exists and reads `false` halts auto-execution — absent or `true` proceeds (auto-execute is the default per N5). |
| G13 | stale-claim | mechanical | Briefs must not rely on stale claims; claim freshness or revalidation must be recorded. |
| G14 | test-execution-silent | mechanical | Risky or high-cost test execution must be requested explicitly rather than silently run. |
| G15 | improve-readme-silent | mechanical | A missing README improvement cannot be silent; the brief must record applied or N/A evidence. |
| G16 | master-current-for-test-evidence | mechanical | Test evidence depending on main/master state must record the base ref used. |

### Gate profiles

Different brief types apply different gate subsets. The default profile is `standard`.

| Profile | Gates applied |
|---|---|
| `standard` | All 16 gates (G1–G16) |
| `no_brainer` | G1, G5, G5b, G7, G8, G9, G12, G13, G14, G16 |
| `test_execution` | G1, G2, G4, G8, G13, G14, G16 |
| `experiment` | G1, G2, G4, G7, G8, G11, G13, G16 |

The `no_brainer` profile skips review and README gates because no-brainer briefs are mechanical and time-constrained. The `experiment` profile requires the breadcrumb gate (G11) since experiments produce artifacts that must be traceable. Stop gates G5 and G5b are enforced only on `standard` and `no_brainer` profiles because those are the paths where automation might otherwise short-circuit human review.

---

## End-to-end workflow

A single brief cycle from artifact to decision proceeds as follows.

1. **Artifact exists.** A branch is merged, a bead is closed with the `needs-decision` label, or human directs `brief-prep <artifact>` explicitly. This produces or identifies the source artifact.

2. **brief-prep fires.** The `brief-prep` skill (or the `on-merge-brief-record` order + formula chain) runs. It calls `grill-and-present` to gather all 10 brief sections, grills on ambiguity, runs tests, FP-converges the brief through `coordinate-review`, and checks `catch-no-brainer` to determine output shape (compact or full-form).

3. **Brief lands in .pile.** The finished brief markdown is written to `~/.gc/mathcity/briefs/.pile/<run-id>/brief.md` with gate evidence in `evidence.toml`. The `brief-shuffle-pile` order's condition check (`find ~/.gc/mathcity/briefs/.pile -name '*.md'`) becomes true.

4. **brief-shuffle promotes or rejects.** The single-writer shuffler picks up the pile item, runs `brief-gate-keep` against the gate registry, and either promotes the brief to `~/.gc/mathcity/briefs/stack/` (appending to `manifest.jsonl`) or rejects it to `.pile/.rejected/` with a reason.

5. **The clerk drains the stack via `present-briefs`.** The outside clerk (or Mayor) runs the `present-briefs` skill — presentation is human-facing and cannot be staffed by a gc order. All pending stack briefs are presented. No-brainer-classified briefs appear as a single collapsed block; full briefs are rendered one at a time through `present-it`. The Decision-at-Top invariant ensures the first content human sees is what is being decided.

6. **human adjudicates.** human issues a verdict: approve, reject, defer, or revise. The `adjudicate-brief` skill records the verdict fields on the brief bead itself (verdict + authorizer + rationale + date — one-bead model), closes the bead, and rings the `brief.decided` event.

7. **Two event-driven orders fire in parallel.** `brief-decision-dispatch` acts on the verdict — merging the source branch on approve, creating a follow-up work bead on reject/revise, or recording a defer marker. `post-decision-file-or-sendback` routes the brief itself: FILE (a successor bead gets re-briefed) or SEND-BACK (the brief archives and the work returns to the originator).

8. **Brief archives.** Either `brief-archive-on-request` fires immediately on a SEND-BACK event, or `brief-archive-sweep` picks up the brief in its next 24h cooldown run. Decision records are never deleted; only the working artifacts move to `~/.gc/mathcity/briefs/archive/`.

---

## The Outside Clerk

The **outside clerk** is a Claude Code session (no `GC_AGENT` env var) assigned
to the adjudication phase of the brief pipeline. The clerk is a strict
intermediary: it presents briefs, captures human verdicts, and dispatches
approved work — it does not write code, edit policy, or run formulas itself.

The clerk is distinct from the Mayor. Both may adjudicate briefs, but
the clerk's PRIMARY job is draining the brief stack. The Mayor coordinates the
city; the clerk reads to the human adjudicator.

### How to start a clerk session

Run `/prime-clerk` at the start of any session assigned to read briefs. It
orients the session on the one-bead model, sets up the agent-inbox channel
to the Mayor, and points to the brief stack.

### The clerk's brief-reading loop

```
/present-briefs          ← drain the stack; presents one brief at a time
                            in unlock_count order (most-unblocking first)
     │
     ▼  human gives a verdict
/adjudicate-brief        ← fork-wrapper: records verdict ON the brief bead,
                            closes it, rings brief.decided; calling session
                            emits one line and stops
     │
     ▼  if APPROVE:
/mathcity.work          ← dispatch the artifact bead to the fleet
                            (build-basic-briefed formula)
     │
     ▼  verify assignee non-empty within ~60s, then present next brief
```

### Key skills for clerk operation

| Skill | Purpose |
|---|---|
| `prime-clerk` | Onboard a fresh clerk session — one-bead model, stack location, inbox setup. |
| `present-briefs` | Drain the brief stack to the human adjudicator, one brief at a time, with a pre-loaded hot queue. |
| `adjudicate-brief` | Record the human verdict on the brief bead (APPROVE / REJECT / REVISE / DEFER) and close it. |
| `mathcity.work` | After APPROVE: dispatch the artifact bead via build-basic-briefed. |
| `communicate-with-other-agent` | V2 daily-folder inbox: send messages to the Mayor, clerk, or repo-side landing agent for questions, holds, or sequencing. |
| `check-plan-hygiene` | REQUIRED before any sling command copied from a brief body. |
| `prime-outsider` | Re-orient after compaction or session clear: finds open beads and restates standing rules. |

### Relationship to the Mayor

The Mayor and the clerk use the **same** two-skill adjudication flow
(`present-briefs` → `adjudicate-brief`). The clerk is not subordinate to the
Mayor for presentation — it dispatches approved briefs directly via
`mathcity.work` without routing through the Mayor. Questions about holds,
sequencing constraints, or ambiguous beads go to the Mayor on the agent-inbox
channel (`communicate-with-other-agent`).

---

## Bead types

See [README-beads.md](README-beads.md) for bead type reference and bead policy.

---

## Bead Backup Setup

See [Dolt remote setup](docs/DOLT-REMOTE-SETUP.md) for private bead-backup
repository naming, remote configuration, two-sided sync, server mode, and
restore steps.

---

## Change Log

**2026-07-14:** Full stale `gc.run-operator` sweep completed (13 formula `default =` occurrences across 12 files + 3 order `pool =` lines retargeted to `mathcity.brief-operator`; beads gt-oiigr / gt-wz0xj / gt-rix5m). No-brainer mode fix applied: `no-brainer-process.toml` now has `[vars] mode = "guarded-execute"` (gt-d3h6e). Gate file `operator_target` defaults deferred (gt-y4nhw P3 — gates still function via order overrides). `gc supervisor start` is now unblocked.

**2026-07-13 (P4.2 migration):** Retired `brief-present-next` order; presentation moved to clerk `present-briefs` skill; `record-decision` → `adjudicate-brief`. The `brief-present-next` ORDER was retired (presentation is human-facing and now lives in the outside clerk's `present-briefs` skill; the FORMULA is kept). Adjudication is recorded via the renamed `adjudicate-brief` skill (formerly `record-decision`), which rings `brief.decided` and fires the machine cascade on the `mathcity.brief-operator` pool. The deterministic machine-step orders were retargeted off the gastown-vestige / non-resolving pools (`dog`, `gc.run-operator`, `mayor`) onto the pack-local, persistent `mathcity.brief-operator` agent.
