# Gascity Restart: Context Reference

> **DO NOT ABRIDGE OR TRUNCATE THE CONTENTS OF THIS FILE WITHOUT EXPLICIT USER AUTHORIZATION.**
> Correct errors in place (P5.4); every section has been verified correct across multiple Mayor sessions.

> Narrative reference for the <city-root> city restart, brief system verification, and hecke #335 work.
> Not a checklist — see gascity-restart-checklist.md for step-by-step.

---

## Pre-Restart Fixes Applied (2026-07-14) — `gc supervisor start` is now unblocked

| Fix | Bead | Status |
|-----|------|--------|
| `no-brainer-process.toml`: added `[vars] mode = "guarded-execute"` | gt-d3h6e | ✓ DONE |
| `orders/on-merge-brief-record.toml`: `pool` → `mathcity.brief-operator` | gt-oiigr | ✓ DONE |
| `orders/brief-shuffle-pile.toml`: `pool` → `mathcity.brief-operator` | gt-wz0xj | ✓ DONE |
| `orders/brief-review-patrol.toml`: `pool` → `mathcity.brief-operator` | gt-rix5m | ✓ DONE |
| Formula defaults sweep: 13 occurrences across 12 formula files | (gt-oiigr context) | ✓ DONE |
| Gate file `operator_target` defaults (4 files) | gt-y4nhw | DEFERRED P3 — gates still function via order overrides |

Verification:
```bash
grep -r "gc.run-operator" <mathcity-pack-root>/ --include="*.toml" | grep -v "^.*:#" | grep -v "gates/"
# → empty
grep "guarded-execute" <mathcity-pack-root>/orders/no-brainer-process.toml
# → mode = "guarded-execute"
```

---

## System Architecture

**Gascity** is a multi-agent orchestration framework. The city at `<city-root>` is a personal
development city managed by the `gc` binary (built from source at `<repos-root>/gascity`).

The city config lives at `<city-root>/city.toml`. All pack imports use **local filesystem paths**
(not remote git refs), so `<repos-root>/gascity-packs/` is the live source for all pack content.
This means rebuilding the `gc` binary does **not** require reinstalling packs — they are read
from disk on every gc invocation.

### Pack Imports (city-wide defaults, all rigs)

| Import key | Source path | Purpose |
|-----------|-------------|---------|
| `gc` | `<gascity-pack-root>/roles` | Base agent roles (polecats, run-operators, dispatchers) |
| `gc-base` | `<gascity-pack-root>` | Base formulas (build-base, build-basic, all gc primitives) |
| `pr-pipeline` | `<repos-root>/gascity-packs/pr-pipeline` | PR author-side workflow formulas (6 mol-pr-* formulas) |
| `mathcity` | `<mathcity-pack-root>` | Brief pipeline orders/formulas, gate registry, math agents |

Hecke additionally imports `mathcity` and `pr-pipeline` at rig scope (D3 pilot, gsp-w88z).

---

## Outside Agents

The city runs two kinds of agents. **Inside agents** are spawned by the gascity
supervisor (`gc sling`, formula steps, orders) and have a `GC_AGENT` environment
variable. **Outside agents** are separate Claude Code sessions opened by the human adjudicator;
they have no `GC_AGENT` and are NOT managed by the gascity process.

### Roster

| Role | Working directory | Responsibility |
|------|-------------------|----------------|
| **Mayor session** | `<city-root>` | Coordinates dispatch, monitors the fleet, adjudicates or routes briefs, and does not commit or push unless explicitly authorized by the local operating policy. |
| **repo-side landing agent** | `<repos-root>/*` | Commits, pushes, and opens PRs in repo-side checkouts after the appropriate authorization gate. |
| **clerk** | `<city-root>` or a repo-side checkout | Presents briefs to the human adjudicator, records verdicts through the brief workflow, and routes questions to the Mayor. |

Local UUIDs and human-readable nicknames are private workspace state. Keep
them in `<city-root>/.claude/inbox/.agent-names.map` or another untracked local note,
not in tracked pack documentation.

### How they spawn

- **Mayor session**: open a Claude Code session with CWD `<city-root>`, then run `/mathcity.mayor-math-prime`. The restart cycle is `mayor-math-handoff` -> `/clear` -> `mayor-math-prime`. If the local inbox is in use, record the session UUID in `<city-root>/.claude/inbox/.agent-names.map`.
- **repo-side landing agent**: open a separate Claude Code session with CWD inside `<repos-root>` when repo-side commits, pushes, or PRs are required.
- **clerk**: open a session assigned to brief presentation and run `/prime-clerk`.
- **Inside gc agents** (`gc.run-operator`, `mathcity.brief-operator`, `core.control-dispatcher`, etc.): spawned entirely by the gascity supervisor in response to sling calls, formula steps, or condition-based orders. They have `GC_AGENT` set and are subject to `gc status`, `gc session logs`, and `gc events`.

### Communication — the agent inbox

Outside agents communicate via the shared inbox at `<city-root>/.claude/inbox/`.

```
<city-root>/.claude/inbox/
  .agent-names.map          # UUID → human name (repo-side-landing-agent, clerk, mayor, ...)
  <name>/<YYYY-MM-DD>/      # canonical per-recipient per-day folder (V2 layout)
    <HH-MM-SS>-from-<sender>-<subject-slug>.md   # ONE file per message
  <UUID>.md                 # flat append (backward-compat monitor target)
```

Send via `bash ~/.claude/scripts/agent-send.sh FROM TO "Subject" /path/to/body.md`
from `<city-root>` (CWD walk-up resolves the inbox base).

Rules:
- One topic per message. ACK before acting on proposals.
- Subject ≤ 80 chars (becomes the filename slug).
- Sign with `-- <uuid-prefix> (<name>)`.
- Do not start cross-agent threads without user approval.

### Division of labor (quick reference)

| Action | Who |
|--------|-----|
| File / update beads | Mayor session (or any agent with bd access) |
| Sling formulas, dispatch fleet | Mayor session |
| Adjudicate briefs | the human adjudicator (Mayor session presents, the human adjudicator decides) |
| Commit + push to example-owner/ remotes | repo-side landing agent only, behind `authorize-git-operation` |
| Create / edit files in `<repos-root>/*` | repo-side landing agent only (LP1 rule) |
| Present briefs to the human adjudicator | clerk |
| Run city audits (`check-city-policy`) | clerk |
| Run `check-plan-hygiene` before a sling | Mayor session |
| Inside fleet work (build, review, publish) | `gc.run-operator`, `gc.publisher`, etc. |

---

## Agent / Pool / Worker Inventory

`gc status` with the city running shows `0/20 agents` when stopped, scaling to ~20 when running.

### Persistent Pools (always-warm)

| Agent | Pool size | Scope | Role |
|-------|-----------|-------|------|
| `mathcity.brief-operator` | min=1, max=12 | city | Runs deterministic brief-pipeline machine steps (shuffle, watchdog, decision dispatch, archive sweeps, no-brainer classification). **Never adjudicates, never presents.** Wake mode: fresh (each claim is a new session). Idle timeout: 2h. |
| `bd.dog` | min=0, max=2 | city | Beads daemon; min=0 means it only starts under load. |

### Per-Rig Persistent Agents (one per rig)

Each of the ~13 active rigs has one `core.control-dispatcher` session that stays running and
routes incoming sling work to the appropriate per-rig workers.

Active rigs: `agent_skills`, `differential_valuations`, `hecke`, `homog`, `jacobi`, `lmfdb`,
`magma_clifford_algebras`, `magma_diff_alg`, `example-owner_github_io`, `gascity`, `gascity-packs`,
`cliff-part2`. Rigs `diff_alg_public`, `diff_alg_problems`, `dupuy_cv` are `suspended_on_start=true`.

### On-Demand Workers

`gc.run-operator` sessions are spun up per-rig on demand when work is slung to a rig and
torn down after draining. As of 2026-07-14, all brief-pipeline rig-scoped orders
(`on-merge-brief-record`, `brief-shuffle-pile`, `brief-review-patrol`) have been retargeted
to `mathcity.brief-operator` (pool sweep gt-oiigr / gt-wz0xj / gt-rix5m).

### Codex Worker

`codex-worker` is a rig-scoped agent using the `codex` provider (`builtin:codex`).
It is `fallback=true` and `permission_mode=no-approval-sandboxed` so managed Codex
sessions can run their Gas City work loop without waiting at approval prompts while
remaining inside the workspace sandbox. Broader access is a local operator opt-in outside
the shipped pack. Dispatched explicitly via the
`codex-dispatch` formula — never by automated orders. Use when an independent non-Anthropic
perspective is needed (cross-model review, design decisions, large proofs).

---

## Brief Pipeline: Full Lifecycle

```
source bead closes (needs-decision label)
        │
        ▼  on-merge-brief-record order (event: bead.closed, rig-scoped)
        │  → on-merge-brief-record formula: creates brief-record bead, touches brief-prep pipeline
        │
        ▼  brief-prep formula (or math-brief-prep for fan-out)
        │  → gates checked (brief-gate-keep), review evidence gathered
        │  → brief.md deposited in .beads/briefs/.pile/<slug>/brief.md
        │
        ▼  brief-shuffle-pile order (condition-trigger, rig-scoped)
        │  check: find .beads/briefs/.pile -mindepth 2 -maxdepth 2 -type f -name 'brief.md'
        │  → brief-shuffle formula: single-writer, promotes .pile → .beads/briefs/stack/
        │
        ▼  /present-briefs skill (CLERK-DRIVEN, not an order)
        │  → brief-present-next formula: drains all stack briefs
        │  → no-brainers collapsed to one-line block; full briefs via grill-and-present
        │
        ▼  /adjudicate-brief skill
        │  → brief-record-decision formula: writes decision record, emits brief.decided event
        │
        ├── brief-decision-dispatch order (event: brief.decided, city-scoped)
        │   → brief-decision-dispatch formula:
        │     approve  → reassign source bead to <rig>/gc.publisher (runs the publish
        │               step: push branch / open PR, no-op by default — does NOT merge to
        │               main; requires `branch` metadata or it dead-ends. P5.4-verified)
        │     reject   → create follow-up bead with reason
        │     revise   → create follow-up bead with feedback
        │     defer    → mark dispatched, no action
        │
        └── post-decision-file-or-sendback order (event: brief.decided, city-scoped)
            → file-or-sendback-route formula:
              FILE     → fire brief-prep for successor bead
              SEND-BACK → request archive (fires brief.archive_requested event)
                          → brief-archive-on-request order catches and archives
```

### Watchdog / Refill

Two orders keep the stack populated:
- `brief-watchdog-refill` (cooldown, 30m) — baseline check
- `brief-watchdog-refill-on-stack-low` (event: `brief.stack-low`) — immediate refill trigger

Both run via `mathcity.brief-operator` pool.

### Review Patrol

`brief-review-patrol` (cooldown, 30m, rig-scoped, `mathcity.brief-operator`) — backstop for briefs
stuck at `review_gate: pending`. Advances them through Phase 5 or escalates.

### Archive Sweep

`brief-archive-sweep` (cooldown, 24h) — moves decided/rejected brief artifacts to archive.
Triggered immediately by `brief.archive_requested` via `brief-archive-on-request` order.

---

## No-Brainer System

The goal of the no-brainer system is to keep work flowing by auto-processing briefs that
are too easy to require the human adjudicator's input. **Current state (2026-07-14): auto-execution is designed,
policy-adopted (N5, 2026-07-12), and wired — `no-brainer-process.toml` now has
`[vars] mode = "guarded-execute"` (gt-d3h6e, applied 2026-07-14). However, auto-execution
is NOT triggered by `gc start` — it is manual-trigger only (see below). Additionally, the
kill-switch is now set: `<city-root>/.beads/auto_merge_enabled` reads `false` → auto-exec HALTED.**

### Classification (works now)

1. `catch-no-brainer` skill (PRELIMINARY v0.2 DRY-RUN) classifies briefs against 5 criteria
   (cat-A stale-branch / cat-B test-exec / cat-C verification / cat-D consolidate-mini).
   Confidence threshold for auto-execute eligibility: ≥ 0.85.
2. `no-brainer-classify` formula — manual trigger via `no-brainer-process` order — classifies
   candidates and copies matches to `.beads/briefs/.pile/.no-brainer/`.
3. `brief-prep` also runs `catch-no-brainer` during brief prep (formula step).

### Compact presentation (works now)

During `/present-briefs`, no-brainer classified briefs appear **collapsed into a single
one-line block** (compact form, CONFIRM: y / n / grill-me-further). adjudication still happens
them — the compact path is a speed-up, not a bypass. `compact_eligible: true` must be set
in the classifier's verdict for a brief to use compact form.

### Full auto-execution (MANUAL TRIGGER ONLY — does NOT fire on `gc start`)

N5 policy (2026-07-12): auto-execute is the DEFAULT intent. The `guarded-execute` step exists
in `no-brainer-classify.toml` and is activated when the order runs with `mode = "guarded-execute"`.
**Fix applied 2026-07-14 (gt-d3h6e):** `no-brainer-process.toml` now has a `[vars]` section
with `mode = "guarded-execute"`.

**CRITICAL CORRECTION:** `no-brainer-process.toml` has `trigger = "manual"` (line 5). The
gascity core scheduler never tick-fires manual orders (`<repos-root>/gascity/internal/orders/triggers.go:72`
— "manual trigger — use gc order run"). Therefore **`gc start` does NOT auto-fire no-brainer
execution.** It runs only via an explicit `gc order run no-brainer-process`.

Additionally, the `he-x3se` pile-processor (which would drain `.pile/.no-brainer/`) **does not
exist** — documentation references only, zero code. So unattended auto-execution is inert
without the manual order.

To trigger no-brainer auto-execution explicitly:
```bash
gc order run no-brainer-process
```

**Kill-switch (now set — doubly gated):**

Auto-execution is doubly gated: (a) it can only run via the manual order at all (trigger=manual),
and (b) even then the kill-switch halts it until set to `true` or removed.

Kill-switch hierarchy (both levels checked; first `false` wins):

- City: `<city-root>/.beads/auto_merge_enabled` — **absent or `true` = auto-execute permitted**; present and reads `false` = HALTED
  - **Current state (2026-07-14, Mayor restart session): file EXISTS and reads `false` → HALTED**
- Rig: `<rig_root>/.beads/auto_merge_enabled` — same semantics; also being set to `false` on the `<repos-root>` side (repo-side landing agent) for defense-in-depth

The gate (`brief-check.sh` `check_no_brainer_execute_safety`) checks, in order: city-level
path first (`${GC_CITY:-$HOME/gt}/.beads/auto_merge_enabled`), then rig-level
(`<rig_root>/.beads/auto_merge_enabled`). Both must be absent or `true` for auto-exec to proceed.
Document and maintain the kill-switch on **both** `<city-root>` and `<repos-root>` sides.

To re-enable auto-execution when ready:
```bash
echo "true" > <city-root>/.beads/auto_merge_enabled
# and on repos side:
echo "true" > <repos-root>/<rig>/.beads/auto_merge_enabled
# or remove both files entirely (absent = auto-execute permitted)
```

Stop gates G5 (server-touching) and G5b (user-skill-touching) prevent auto-execution
regardless of kill-switch state. Also blocked: confidence < 0.85, any non-no-brainer
category, and `user_skill_touching_override: true` in the brief record.

---

## PR Pipeline

> **Note on "pr-pipeline branch":** `pr-pipeline` here refers to the **pack** at `<repos-root>/gascity-packs/pr-pipeline/` — a subdirectory of gascity-packs, not a git branch. The pack is already imported city-wide via `city.toml`. There is no separate `pr-pipeline` git branch to switch to; all mol-pr-* formulas are live on disk at that path.

Six formulas shipped in `<repos-root>/gascity-packs/pr-pipeline/`, already imported city-wide:

| Formula | Command surface | Purpose |
|---------|----------------|---------|
| `mol-pr-start` | `gc pr-pipeline pr plan <issue>` | Issue → structured plan (no code written) |
| `mol-pr-blast-radius` | `gc pr-pipeline pr blast-radius "<scope>"` | Map impact surface of a proposed change |
| `mol-pr-review` | `gc pr-pipeline pr review <pr>` | 11-category outgoing-PR self-review scorecard |
| `mol-pr-ship` | `gc pr-pipeline pr ship` | Pre-push gate: simplify → review → checks → readiness report |
| `mol-pr-triage` | (sling directly) | Scan/classify open upstream issues into ranked work-queue |
| `mol-pr-from-issue` | `gc sling <rig>/gc.run-operator mol-pr-from-issue --formula --var issue_number=<N>` | Macro chain: issue → plan → ship → branch-ready PR |

`mol-pr-from-issue` is the full author-side macro. It does NOT push or open a PR by default
(`auto_push=false`). Add `--var auto_push=true` only when the human adjudicator has explicitly authorized.

---

## Mathcity Subdomains

The `mathcity` pack is organized into subdomains under `<mathcity-pack-root>/subdomains/`:

`brief-system`, `computing`, `dev`, `latex`, `lmfdb`, `magma`, `proof-assist`

**Name mapping:** `mathcity-brief-system` in discussion refers to the `brief-system` subdomain; `mathcity-dev` refers to the `dev` subdomain. Directory names are the canonical form (no `mathcity-` prefix in the filesystem).

---

## Formulas / Orders / Agents Reference Table

### Mathcity Orders (`<mathcity-pack-root>/orders/`)

| Order name | Source file | Trigger | Scope | Pool | What it does |
|------------|-------------|---------|-------|------|-------------|
| `on-merge-brief-record` | `on-merge-brief-record.toml` | event: `bead.closed` | rig | `mathcity.brief-operator` | Creates brief-record bead for closed `needs-decision` beads |
| `brief-shuffle-pile` | `brief-shuffle-pile.toml` | condition (pile has brief.md) | rig | `mathcity.brief-operator` | Promotes .pile briefs → .stack (single-writer) |
| `brief-decision-dispatch` | `brief-decision-dispatch.toml` | event: `brief.decided` | city | `mathcity.brief-operator` | Acts on verdict: on approve reassigns source bead to `<rig>/gc.publisher` (publish step: push/PR, no-op default, NOT a merge-to-main; dead-ends on no-`branch` beads — see gt-yv8p2); on reject/revise creates follow-up bead; on defer no-ops |
| `post-decision-file-or-sendback` | `post-decision-file-or-sendback.toml` | event: `brief.decided` | city | `mathcity.brief-operator` | Routes FILE or SEND-BACK for decided brief |
| `brief-archive-on-request` | `brief-archive-on-request.toml` | event: `brief.archive_requested` | city | `mathcity.brief-operator` | Archives sent-back brief immediately |
| `brief-archive-sweep` | `brief-archive-sweep.toml` | cooldown: 24h | city | `mathcity.brief-operator` | Sweeps old decided/rejected artifacts to archive |
| `brief-review-patrol` | `brief-review-patrol.toml` | cooldown: 30m | rig | `mathcity.brief-operator` | Unsticks briefs at `review_gate: pending` |
| `brief-watchdog-refill` | `brief-watchdog-refill.toml` | cooldown: 30m | city | `mathcity.brief-operator` | Checks stack depth; fires brief-prep if below watermark |
| `brief-watchdog-refill-on-stack-low` | `brief-watchdog-refill-on-stack-low.toml` | event: `brief.stack-low` | city | `mathcity.brief-operator` | Immediate refill trigger on stack-low event |
| `no-brainer-process` | `no-brainer-process.toml` | manual | city | `mathcity.brief-operator` | Classify no-brainer candidate under shortcut policy |

### Mathcity Formulas (`<mathcity-pack-root>/formulas/`)

| Formula | Source file | When used |
|---------|-------------|-----------|
| `brief-prep` | `brief-prep.toml` | Produces one policy-gated brief from a source bead |
| `math-brief-prep` | `math-brief-prep.toml` | Fan-out brief-prep: one instance per pending source bead, then shuffle |
| `on-merge-brief-record` | `on-merge-brief-record.toml` | Fired by `on-merge-brief-record` order; creates brief-record bead |
| `brief-shuffle` | `brief-shuffle.toml` | Single-writer pile→stack promotion; fired by `brief-shuffle-pile` order |
| `brief-present-next` | `brief-present-next.toml` | Drain all stack briefs (no-brainers collapsed); used by `/present-briefs` |
| `brief-record-decision` | `brief-record-decision.toml` | Write canonical decision record; emits `brief.decided` |
| `brief-decision-dispatch` | `brief-decision-dispatch.toml` | Acts on verdict after `brief.decided` |
| `file-or-sendback-route` | `file-or-sendback-route.toml` | Routes FILE/SEND-BACK for decided brief |
| `brief-archive-sweep` | `brief-archive-sweep.toml` | Moves decided/rejected artifacts to archive (vapor phase) |
| `brief-gate-keep` | `brief-gate-keep.toml` | Runs gate registry against a staged brief |
| `brief-watchdog-refill` | `brief-watchdog-refill.toml` | Measures stack depth; opens brief-prep work if needed |
| `no-brainer-classify` | `no-brainer-classify.toml` | Classifies brief candidate; optionally auto-executes (guarded) |
| `brief-review-patrol` | `brief-review-patrol.toml` | Advances stuck `review_gate: pending` briefs |
| `codex-dispatch` | `codex-dispatch.toml` | Dispatches task to codex-worker for cross-model review; **never fired by automated orders** |
| `upf-experiment-dispatch` | `upf-experiment-dispatch.toml` | Qualifies and dispatches experiment to UPF with breadcrumbs |
| `test-execution-request` | `test-execution-request.toml` | Formal test-execution request workflow |
| `decision-enforce` | `decision-enforce.toml` | Enforces bd-decision-canonical principle (record existence + verdict/bead alignment) |

### PR Pipeline Formulas (`<repos-root>/gascity-packs/pr-pipeline/formulas/`)

| Formula | Source file | When used |
|---------|-------------|-----------|
| `mol-pr-start` | `mol-pr-start.formula.toml` | Issue → structured plan (no code written) |
| `mol-pr-blast-radius` | `mol-pr-blast-radius.formula.toml` | Map impact surface; standalone or composed |
| `mol-pr-review` | `mol-pr-review.formula.toml` | 11-category outgoing-PR scorecard |
| `mol-pr-ship` | `mol-pr-ship.formula.toml` | Pre-push gate; produces readiness report |
| `mol-pr-triage` | `mol-pr-triage.formula.toml` | Scan/classify open upstream issues |
| `mol-pr-from-issue` | `mol-pr-from-issue.formula.toml` | Macro chain: issue → branch-ready PR |

### Key Events

| Event | Emitted by | Caught by |
|-------|-----------|-----------|
| `bead.closed` | Beads system | `on-merge-brief-record` order |
| `brief.decided` | `brief-record-decision` formula (emit-decided-event step) | `brief-decision-dispatch` order, `post-decision-file-or-sendback` order |
| `brief.archive_requested` | `file-or-sendback-route` formula | `brief-archive-on-request` order |
| `brief.stack-low` | `assets/scripts/brief-stack-low.sh --emit` (post-decision hook, gsp-xhc); script measures 3 signals (approved ≤ threshold, total ≤ threshold, unlock_pos ≤ threshold); emits only when `--emit` flag is passed | `brief-watchdog-refill-on-stack-low` order |

---

## Correct Command Surface

All commands verified against `gc --help` and subcommand help. Commands **not** present
in the actual gc binary are flagged.

### Status and Health

```bash
gc status                        # city-wide overview: controller state, agent pool scales, session counts
gc doctor                        # workspace health check; run after rebuild or restart
gc config show                   # resolve + dump city.toml (errors if malformed); `check` subcommand does NOT exist
gc config explain                # resolved config annotated with per-key provenance
gc costs                         # per-run usage and estimated cost
```

### Start / Stop / Reload

```bash
gc start                         # start city under machine-wide supervisor
gc stop <city-root>                     # stop city (controller + all sessions)
gc reload                        # HOT-RELOAD: re-read city.toml without restart; picks up pack/config changes
gc service restart               # bounce the launchd service (needed after binary rebuild)
gc suspend                       # suspend all agents (no stop)
gc resume                        # resume a suspended city
```

### Sessions (runtime operations moved from `gc agent`)

```bash
gc session list                                    # all sessions (active + suspended)
gc session list --template mathcity.brief-operator # filter by agent template
gc session list --state active                     # only running sessions
gc session peek <session-id>                       # view session output without attaching
gc session logs <session-id>                       # show session logs (key for formula debugging)
gc session attach <session-id>                     # attach to running session
gc session nudge <session-id> "text"               # send message to session
gc session kill <session-id>                       # force-kill (reconciler restarts)
gc session suspend <session-id>                    # suspend one session
```

**Note**: `gc agent` manages configuration (add/list/suspend/resume agent definitions).
Runtime operations (peek, logs, nudge, kill) are under `gc session`.

### Orders

```bash
gc order list                    # list all available orders
gc order list --rig hecke        # rig-scoped orders for hecke
gc order show <name>             # show order config (trigger, formula, pool, interval)
gc order check [name]            # check which orders are due to run
gc order history [name]          # show past execution history; best for "did this order run?"
gc order history brief-shuffle-pile --rig hecke  # history for one order in one rig
gc order run <name>              # execute an order manually (NOT "gc order fire")
gc order run brief-shuffle-pile --rig hecke      # manual trigger for rig-scoped order
```

### Formulas

```bash
gc formula list                  # list all available formulas (from all imported packs)
gc formula list --rig hecke      # rig-scoped view
gc formula show <name>           # show compiled recipe (steps, vars, trigger)
gc formula cook <name>           # instantiate a formula into the bead store (advanced)
gc formula version-check <bead>  # check if a bead's formula matches current on-disk version
```

### Events (NOT `gc event log` — that command does not exist)

```bash
gc events                        # list recent events (JSON lines)
gc events --type bead.closed --since 1h          # filter by type + time window
gc events --type brief.decided --since 30m       # watch for decision events
gc events --follow                               # stream events continuously (tail -f equivalent)
gc events --watch --type brief.decided --timeout 5m  # block until event arrives
gc event emit <type> [--payload k=v]             # emit an event (gc event, singular, only has emit)
```

### Sling

`gc sling` is the dispatch op that **creates and routes work in one motion**. Depending on
the second argument it can route an existing bead to an agent, auto-create a new bead from
inline text and route it, or fire a named formula against a pool. When a formula is slung,
gascity materializes its steps as beads and drives the run outside your session — the job
persists even if your session ends.

```bash
# gc sling [target] <formula-or-bead-or-text> [flags]
# target is optional (uses rig default_sling_targets if omitted); required with --formula to a pool

# Route an existing bead to an agent
gc sling mayor <bead-id>
gc sling hecke/gc.run-operator <bead-id>

# Create a bead from inline text and route it (requires explicit target)
gc sling mayor "write a README for hecke"

# Dispatch a formula (--formula makes second arg a formula name)
gc sling hecke/gc.run-operator brief-prep --formula --var source=he-xxxx --var brief_slug=he-xxxx-brief
gc sling hecke/gc.run-operator mol-pr-from-issue --formula --var issue_number=335

# Route existing bead and attach a formula (required for v2 formulas with {{convoy_id}} or drain steps)
gc sling hecke/gc.run-operator <bead-id> --on <formula-name>

# Default-target route (omit target; rig prefix picks from default_sling_targets at random)
gc sling <bead-id>

# Dry-run to see what would happen
gc sling --dry-run hecke/gc.run-operator brief-prep --formula
```

### Import / Pack

```bash
# Packs are LOCAL PATHS — no reinstall needed after gc binary rebuild
gc import check                  # validate import state
gc import status                 # show declared imports and packs.lock pins
gc import list                   # list imported packs
gc pack list                     # show remote pack sources (informational)
# gc import install is for remote packs; not needed here
```

### Analysis / Debugging

```bash
gc analyze reliability           # correlate session-lifecycle events with model/rig
gc order history <name>          # when did this order last run? did it succeed?
gc session logs <id>             # what did this formula run actually do?
gc costs                         # token/cost accounting per run
```

---

## Pack Installation from a Fresh Binary Rebuild

Since `<city-root>/city.toml` imports all packs as **local paths** pointing to `<repos-root>/gascity-packs/`,
rebuilding the `gc` binary from source does **not** require any pack reinstallation. Packs are
read live from disk on every invocation.

Full procedure after a source rebuild:

```bash
# 1. Rebuild the gc binary
cd <repos-root>/gascity
make install            # installs to $(GOPATH)/bin/gc
gc version              # verify the new build is on PATH

# 2. (Optional) Rebuild bd if beads source changed
cd <repos-root>/beads
make install
bd version

# 3. Validate city config reads correctly with the new binary
cd <city-root>
gc config check         # must pass before starting
gc import check         # confirm local-path imports resolve
gc import status        # review pins (all local-path → no pins expected)

# 4. Run doctor before starting
gc doctor               # must return healthy

# 5. Start city (or use service restart if already running under launchd)
gc start                # start under supervisor
# OR, if already registered as a service:
gc service restart      # bounce without re-registering

# 6. Verify pools warm up
gc status               # expect: mathcity.brief-operator-1 starting/running within 60s
gc session list --template mathcity.brief-operator

# 7. Verify orders are visible
gc order list | grep brief
gc formula list | grep mol-pr
```

---

## Fan-Out / Fan-In Pattern

Used for epic decomposition. A convoy groups related beads; the convoy auto-closes
when all member beads close.

```bash
# 1. Create an epic bead in the rig
bd create "Epic title" --type epic --rig hecke

# 2. Create a convoy attached to the epic (via /create-convoy skill)
# The convoy tracks member beads and auto-closes when all tracked issues close.
# OWNED convoys (created with --owned) do NOT auto-close; end them with: gc convoy land <id>

# 3. Fan out: create sub-beads and sling them to workers
# Each sub-bead is dispatched independently; workers run in parallel.

# 4. Monitor convoy state
gc convoy status <convoy-id>    # member count, completion status (NOT `convoy show` — that subcommand does not exist)
bd show <convoy-id>             # convoy bead notes

# 5. Completion: convoy auto-closes via gc convoy check when ALL tracked issues are closed.
# There is no join/barrier step — it is an all-children-done rollup check.
# The convoy.closed event fires and can trigger a finalize formula step.
```

The `math-brief-prep` formula uses this pattern internally: fan-out `brief-prep` instances
per pending source bead (drain), then single-writer shuffle after the fan-in.

### build-basic Full-Lifecycle Fan-Out

The `build-basic` formula (from `gascity/`) is the standard full-lifecycle
template: requirements → plan → plan-review → decompose → implement (drain) → review →
publish. The `implement` step fans out to as many `gc.implementation-worker` sessions as
the `decompose` step created sub-beads, running them in parallel via convoy tracking.
Workers are on-demand `gc.run-operator`-class agents; the controller queues against the
active cap. The publish step hands the work to `gc.publisher`, which **pushes the feature branch / opens a PR** and is a **no-op by default** (`push`/`open_pr`=false) — it does **NOT** merge to main (P5.4-verified against `publish.formula.toml` + `build-basic/publish.md`; nothing in gascity or core merges to main). To fire it:

```bash
gc sling hecke/gc.run-operator <bead-id> --on build-basic
# or with a formula dispatch:
gc sling hecke/gc.run-operator build-basic --formula --var issue_number=<N>
```

---

## Work Resurfacing (HELD Beads)

When a bead is set to **HELD** status it is paused pending an external condition — typically a
human decision, upstream data dependency, or an explicit gate. Assigned agents do **not**
automatically re-pick up work when a hold is released; the human adjudicator must re-sling the bead.

### What a HELD bead looks like

```bash
bd show he-hw5z4
# Status:   HELD
# Assignee: hecke/mayor
# Labels:   ...
# Notes:    "HELD pending: dolt sync to <city-root> + the human adjudicator OK for 95-item batch"
```

`Status: HELD` in `bd show` output indicates the bead is on hold. The assignee field still
shows who was working on it before the hold was placed.

### Releasing a hold

```bash
# Remove the hold and return the bead to open status:
bd update he-hw5z4 --remove-hold

# If that flag isn't recognized, check installed flag names:
bd update --help | grep -i hold

# Fallback (sets status to open without touching the hold flag):
bd update he-hw5z4 --status open
```

After releasing, confirm:
```bash
bd show he-hw5z4   # expect: Status: OPEN
```

### Resuming work after hold release

Gascity does **not** automatically re-dispatch a bead when a hold is released — the assigned
agent's session has usually ended. The human adjudicator must explicitly re-sling:

```bash
# General form:
gc sling <assignee-path> <bead-id>

# For he-hw5z4, assigned to hecke/mayor:
gc sling hecke/mayor he-hw5z4
```

### Concrete unblock flow for he-hw5z4

he-hw5z4 is HELD + assigned to `hecke/mayor`. Unblock sequence:

1. Confirm prerequisites met: dolt sync + the human adjudicator OK for 95-item batch (see hecke-335-recycled-plan.md Known Blockers)
2. Release hold: `bd update he-hw5z4 --remove-hold`
3. Verify status changed: `bd show he-hw5z4` (expect `Status: OPEN`)
4. Re-sling to resume: `gc sling hecke/mayor he-hw5z4`
5. Monitor: `gc session logs <mayor-session-id>` or `gc events --follow`

---

## Worker Capacity Assessment

With the city running:

| Pool | Min | Max | Notes |
|------|-----|-----|-------|
| `mathcity.brief-operator` | 1 | 2 | Always-warm; handles all brief-pipeline machine steps |
| `bd.dog` | 0 | 2 | Starts under load only |
| `codex-worker` | 0 | 1 (per rig) | Fallback=true; on-demand only |
| Per-rig `core.control-dispatcher` | 1 | 1 | ~13 rigs |
| `gc.run-operator` (per rig) | 0 | N | On-demand; spun up when work is slung |
| `gc.publisher` (per rig) | 0 | N | On-demand; picks up approved beads and runs the **publish** step — pushes the feature branch / opens a PR, **no-op by default** unless authorized (`push`/`open_pr`=false). Does **NOT** merge to main (no build/publish path in gascity or core merges; the gastown "refinery merge" was removed 2026-07-09/ba2ff381). P5.4-verified. |

**Is this enough?** For the hello-world smoke test (2 rigs, sequential briefs), yes.
For high-throughput scenarios (many concurrent brief-preps), `math-brief-prep` fans out
as many `gc.run-operator` sessions as there are pending briefs — the controller manages
the queue. The `mathcity.brief-operator` pool at max=12 is the potential bottleneck for
the city-scope machine steps; `brief-review-patrol` and `brief-shuffle-pile` rig-scope
steps use `gc.run-operator` (on-demand, unbounded effectively).

Pools (min/max_active_sessions in agent.toml) **are still a first-class concept** in gascity.
The `fallback=true` flag in `agent.toml` (as seen in codex-worker) is distinct — it means
"fall back to this agent if the primary is unavailable." The `min_active_sessions=1` floor
ensures the brief-operator is always ready without waiting for demand.
