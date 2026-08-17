# Gascity Restart & Brief System Verification Checklist

Parent: [../README-mayor.md](../README-mayor.md)

> **DO NOT ABRIDGE OR TRUNCATE THE CONTENTS OF THIS FILE WITHOUT EXPLICIT USER AUTHORIZATION.**
> Correct errors in place (P5.4); every section has been verified correct across multiple Mayor sessions.

**City:** `<city-root>`
**Date:** 2026-07-14
**Goal:** Confirm brief pipeline, no-brainer system, and PR pipeline work end-to-end after binary rebuild and city restart.

---

## Phase 0 — Pre-Restart Fixes (COMPLETE 2026-07-14)

> These were applied before `gc supervisor start`. All verified; controller start is unblocked.

- [x] **Pool sweep** — `gc.run-operator` retargeted to `mathcity.brief-operator` in 3 order files and 13 formula occurrences (gt-oiigr, gt-wz0xj, gt-rix5m)
- [x] **No-brainer mode** — `[vars] mode = "guarded-execute"` added to `no-brainer-process.toml` (gt-d3h6e)
- [ ] **Gate file defaults** (DEFERRED gt-y4nhw P3) — 4 gate files still have stale `operator_target` defaults; calling orders can override at restart, so not blocking

---

## Phase 0.5 — Pre-flight

> Run these before touching the city. They are read-only and safe.

- [ ] **Check gc version**
  ```bash
  gc version
  ```
  Expected: `dev` (built from `<repos-root>/gascity`). If you see a brew version, the source build isn't on PATH.

- [ ] **Check bd version**
  ```bash
  bd version
  ```
  Expected: `1.1.0` (303e263fe or later).

- [ ] **Validate city.toml**
  ```bash
  gc config show      # resolves + dumps city config as TOML; errors if malformed
  # gc config explain # same, annotated with provenance (which pack set each key)
  ```
  Expected: config resolves and prints with no error. (`gc config check` does NOT exist in this build — verified 2026-07-14.) Deeper health validation is `gc doctor` (Phase 2); import validation is `gc import check` below.

- [ ] **Confirm local-path packs are readable**
  ```bash
  gc import check
  ```
  Expected: all imports report OK. Errors here mean a pack source path is broken or missing — fix the path in city.toml before starting.

  > **Note:** Packs are configured as local paths in city.toml. Gas City base packs live under `<repos-root>/gascity-packs/...`; mathcity lives at `<repos-root>/mathcity`. Binary rebuilds do NOT require reinstalling packs — they are read live from disk.

- [ ] **Review import status**
  ```bash
  gc import status
  ```
  Expected: shows `gc`, `gc-base`, `mathcity`, `contributing` present for defaults, plus the hecke-scoped `mathcity` import. (P5.4 update 2026-07-21 Q23: `contributing` pack added to defaults.rig.imports per the human adjudicator standing requirement.)

---

## Phase 1 — Binary Rebuild (conditional)

> **Skip this phase** if `gc version` already shows the build you want and there are no pending source changes in `<repos-root>/gascity` or `<repos-root>/beads`.

> **⚠️ SCHEMA MISMATCH GUARD (P5.4 Q23, 2026-07-21):** The gc binary embeds the beads library from go.mod (`github.com/steveyegge/beads`). If `bd version` reports a HIGHER schema than `gc`'s embedded beads knows, the city will hang at `starting_bead_store`. Check via `gc supervisor logs | grep "binary knows up to"`. Workaround: add `GC_BEADS_FORCE_FALLBACK=1` to the launchd plist (`~/Library/LaunchAgents/com.gascity.supervisor.plist`), reload, then start. Permanent fix: add `replace github.com/steveyegge/beads => <repos-root>/beads` to `<repos-root>/gascity/go.mod` and rebuild (repo-side landing agent lane). **NOTE: `gc supervisor install --force` / `gc start` overwrites the plist** — re-add `GC_BEADS_FORCE_FALLBACK=1` after any reinstall.

- [ ] **Stop the city first** (if running)
  ```bash
  gc stop
  ```

- [ ] **Rebuild gc**
  ```bash
  cd <repos-root>/gascity
  make install
  gc version
  ```
  Expected: new version string reflects your changes.

- [ ] **Rebuild bd (if needed)**
  ```bash
  cd <repos-root>/beads
  make install
  bd version
  ```

- [ ] **Recheck pack imports after rebuild**
  ```bash
  gc import check
  ```
  Binary change does not affect local-path packs, but run this to confirm nothing broke.

---

## Phase 2 — City Start

- [ ] **Start the city**
  ```bash
  cd <city-root>
  gc start
  ```

- [ ] **Check city status**
  ```bash
  gc status
  ```
  Look for:
  - `Controller: running`
  - `mathcity.brief-operator scaled (min=0, max=3)` — pool starts empty; a member spins up on demand (first claim pays a cold start)
  - All rig dispatchers listed (not all need to be running yet)

- [ ] **Wait for brief-operator to come up** (within ~60s)
  ```bash
  gc session list --template mathcity.brief-operator
  ```
  Expected: `mathcity.brief-operator-1` state = `active` (or transitioning to active). If it stays stopped after 90s, check logs:
  ```bash
  gc session logs mathcity.brief-operator-1
  ```

- [ ] **Run health check**
  ```bash
  gc doctor
  ```
  Expected: all checks PASS. Common warning: order intervals — these are intentionally raised in city.toml (5m dolt-health, 10m gate-sweep, 15m order-tracking-sweep) to avoid jitter false positives; ignore those specific warnings.

- [ ] **Confirm brief pipeline orders are armed**
  ```bash
  gc order list | grep brief
  ```
  Expected: `brief-shuffle-fast-drain`, `brief-review-patrol`, `brief-watchdog-refill`, `brief-watchdog-refill-on-stack-low`, `brief-archive-sweep`, `brief-decision-dispatch`, `no-brainer-process`, `on-merge-brief-record`, `post-decision-file-or-sendback` all present.

- [ ] **Confirm formulas are visible**
  ```bash
  gc formula list | grep brief
  gc formula list | grep -E 'pr-pipeline-briefed|create-issue-briefed'
  ```
  Expected `brief-*`: `brief-prep`, `brief-shuffle`, `brief-archive-sweep`, `brief-record-decision`, `brief-watchdog-refill`, `brief-review-patrol`, `brief-gate-keep`, `brief-present-next` (legacy, OK if present), `math-brief-prep`, `no-brainer-classify`, `on-merge-brief-record`, `file-or-sendback-route`.

  Expected briefed GitHub handoffs: `pr-pipeline-briefed`, `create-issue-briefed`.

---

## Phase 3 — Checking Whether Orders Are Running

Use these commands to diagnose order health at any point:

```bash
# See all available orders with trigger types
gc order list

# Inspect one order's trigger condition and schedule
gc order show brief-shuffle-fast-drain

# See which orders are currently due to fire (based on cooldown/schedule)
gc order check

# See when an order last ran — BEST debugging tool
gc order history brief-shuffle-fast-drain
gc order history brief-shuffle-fast-drain --rig hecke
gc order history on-merge-brief-record

# Manually fire an order (useful for smoke tests — bypasses cooldown)
gc order run brief-shuffle-fast-drain --rig hecke

# Watch orders firing in real-time (all events)
gc events --type order.fired --since 30m
gc events --follow
```

**What to check if an order isn't running:**
1. `gc order show <name>` — confirm trigger type and condition
2. `gc order history <name>` — see if it ran at all; if never, the order may not be resolving to any session
3. `gc session list --template mathcity.brief-operator` — confirm the pool that serves the order is active
4. Check order cooldown: if it fired recently, it's in cooldown (expected behavior)

---

## Phase 4 — Checking Whether Formulas Are Complete

```bash
# List all available formulas
gc formula list

# Inspect a compiled formula recipe (shows steps)
gc formula show brief-prep
gc formula show pr-pipeline-briefed
gc formula show create-issue-briefed

# Check if a running bead's formula version matches what's on disk
gc formula version-check <bead-id>
```

**To check if a specific formula RUN completed:**
```bash
# 1. Find the root bead of the formula run
bd show <bead-id>

# 2. Check for child beads (formula steps create child wisps)
bd list --parent <bead-id>

# 3. If all child wisps are closed → formula completed
# If a child is still open → formula is in progress at that step

# 4. Check session logs for what the agent actually did
gc session list --state all   # find the session ID
gc session logs <session-id>

# 5. Filter events for a formula's beads
gc events --type bead.closed --since 1h
gc events --type bead.created --since 30m
```

---

## Phase 5 — Determining Whether Events Are Firing

```bash
# All events in last 5 minutes
gc events --since 5m

# Filter by event type
gc events --type bead.closed --since 1h
gc events --type bead.created --since 30m

# Block until the next matching event arrives (good for waiting on brief.decided)
gc events --watch --type brief.decided

# Continuous stream (Ctrl+C to stop)
gc events --follow

# Correlate events to order runs
gc order history brief-shuffle-fast-drain
```

**Key event types in the brief pipeline:**

| Event type | Meaning |
|---|---|
| `bead.created` | A new bead (or wisp) was filed |
| `bead.closed` | A bead closed — triggers `on-merge-brief-record` if labeled `needs-decision` |
| `brief.decided` | the human adjudicator adjudicated a brief |
| `order.fired` | An order dispatched work |
| `session.started` | An agent session came up |
| `convoy.closed` | All convoy members completed (fan-in signal) |

---

## Phase 6 — Hello World Brief (Run on Hecke + Homog in Parallel)

> Do hecke and homog simultaneously to test multi-rig routing.

### Hecke

- [ ] **Create a test bead with `needs-decision` label**
  ```bash
  cd <repos-root>/hecke
  bd create "Hello World test brief — hecke smoke test" --type task --label needs-decision
  # note the ID: he-xxxx
  ```

- [ ] **Close it to trigger `on-merge-brief-record`**
  ```bash
  bd close he-xxxx --reason "hello-world smoke test complete"
  ```

- [ ] **Confirm the order saw it** (may need to wait for tick or run manually)
  ```bash
  gc order history on-merge-brief-record --rig hecke
  # Or trigger manually:
  gc order run on-merge-brief-record --rig hecke
  ```

- [ ] **Trigger the shuffle** (promotes from pile to stack)
  ```bash
  gc order run brief-shuffle-fast-drain --rig hecke
  ls <repos-root>/hecke/.beads/briefs/stack/
  ```
  Expected: a brief entry appears in the stack directory.

### Homog

- [ ] **Create a test bead with `needs-decision` label**
  ```bash
  cd <repos-root>/homog
  bd create "Hello World test brief — homog smoke test" --type task --label needs-decision
  # note the ID: ho-xxxx
  ```

- [ ] **Close it to trigger `on-merge-brief-record`**
  ```bash
  bd close ho-xxxx --reason "hello-world smoke test complete"
  ```

- [ ] **Confirm the order saw it** (may need to wait for tick or run manually)
  ```bash
  gc order history on-merge-brief-record --rig homog
  # Or trigger manually:
  gc order run on-merge-brief-record --rig homog
  ```

- [ ] **Trigger the shuffle** (promotes from pile to stack)
  ```bash
  gc order run brief-shuffle-fast-drain --rig homog
  ls <repos-root>/homog/.beads/briefs/stack/
  ```
  Expected: a brief entry appears in the stack directory.

### Present and Adjudicate

- [ ] **Present briefs** (run in clerk session or your session)
  ```bash
  /present-briefs
  ```
  Expected: both hecke and homog briefs appear.

- [ ] **Adjudicate**
  ```bash
  /adjudicate-brief
  ```
  Issue verdict: `approve`, `reject`, `defer`, or `revise`.

- [ ] **Confirm cascade fired**
  ```bash
  gc events --type order.fired --since 5m
  gc order history brief-decision-dispatch
  ```

- [ ] **Confirm brief moved to archive**
  ```bash
  ls <repos-root>/hecke/.beads/briefs/archive/
  ```

---

## Phase 7 — No-Brainer System

- [ ] **Create a clear no-brainer candidate** (pure doc fix, no server touch, no gate trips)
  ```bash
  cd <repos-root>/hecke
  bd create "Fix typo in README.md — no-brainer smoke test" --type task --label needs-decision
  bd close he-yyyy --reason "typo fixed"
  gc order run brief-shuffle-fast-drain --rig hecke
  ```

- [ ] **In `/present-briefs`, confirm collapsed display**
  Expected: no-brainer briefs appear as a single collapsed one-line block, not a full brief card.

- [ ] **Check auto-execute kill-switch**
  ```bash
  cat <city-root>/.beads/auto_merge_enabled 2>/dev/null || echo "absent (auto-execute permitted)"
  ```
  - **Current state (2026-07-14):** file EXISTS and reads `false` → no-brainers PAUSED / auto-exec HALTED.
    Both city-level (`<city-root>/.beads/auto_merge_enabled`) and rig-level (`<rig_root>/.beads/auto_merge_enabled`)
    kill-switches are being set for defense-in-depth. The gate checks city-level first, then rig-level;
    first `false` wins.
  - Absent or `true` → auto-execute permitted (no-brainers can execute when the manual order is run)
  - Present and `false` → no-brainers pause for the human adjudicator confirmation / auto-exec HALTED
  - **Note:** auto-execution is manual-order-only regardless of the kill-switch.
    `no-brainer-process.toml` has `trigger = "manual"`; `gc start` never auto-fires it.
    Testing N-autoexec in this phase requires an explicit `gc order run no-brainer-process`.

- [ ] **Confirm auto-archive (if kill-switch absent/true)**
  ```bash
  ls <city-root>/.beads/briefs/.pile/.no-brainer/ 2>/dev/null
  ```

---

## Phase 8 — Briefed GitHub Handoff Verification

- [ ] **Confirm both briefed handoff formulas are present**
  ```bash
  gc formula list | grep -E 'pr-pipeline-briefed|create-issue-briefed'
  ```
  Expected: `pr-pipeline-briefed`, `create-issue-briefed`

- [ ] **Inspect both formulas**
  ```bash
  gc formula show pr-pipeline-briefed
  gc formula show create-issue-briefed
  ```

- [ ] **Dry-run the briefed PR handoff to confirm routing resolves**
  ```bash
  gc sling hecke/gc.run-operator pr-pipeline-briefed --formula --dry-run
  ```
  Expected: shows what would be dispatched, no error about unresolvable target.

- [ ] **Dry-run the briefed issue handoff to confirm routing resolves**
  ```bash
  gc sling hecke/gc.run-operator create-issue-briefed --formula --dry-run
  ```
  Expected: shows what would be dispatched, no error about unresolvable target.

- [ ] **File Work D bead (TimeLimit patch — independent, no server touch, can run in parallel)**
  ```bash
  cd <repos-root>/hecke
  bd create "Add TimeLimit parameter to find_cyclic_fix in package-certify.mag" \
    --type task \
    --notes "Item 3.2_2.m64.64.8.1.4.2.1.1.19.1 (ng=17, 567K letters) times out at 120s. \
The 866-item REORDER corpus may have more such cases. See he-hw5z4 notes (absorbed from he-4hghs)."
  # sling the new bead:
  gc sling hecke/gc.run-operator <new-bead-id>
  ```
  See hecke-335-recycled-plan.md §Work D for full context.

---

## Phase 9 — Worker Capacity Assessment

```bash
gc status
```

**Current worker layout:**

| Agent | Type | Min | Max | Purpose |
|---|---|---|---|---|
| `mathcity.brief-operator` | scaled pool | 1 | 3 | Brief pipeline machine steps |
| `bd.dog` | scaled pool | 0 | 2 | Bead watchdog / health |
| `codex-worker` | on-demand | 0 | N | Codex-dispatched work |
| `core.control-dispatcher` | 1 per rig | 1 | 1 | Per-rig order routing |
| `gc.run-operator` | on-demand | 0 | N | Dispatched formula runs |

**Assessment:** For a personal dev setup with the brief system and briefed PR/issue handoffs on 2–3 active rigs, 3 brief-operators is the current temporary cap. Workaround `gt-rr2gz1` tracks retiring or justifying this cap after the gascity/runtime order-history and startup root causes are resolved.

- [ ] **Check for pool exhaustion signals**
  ```bash
  gc events --type session.pool-exhausted --since 1h
  ```

- [ ] **Hot-reload config after any agent.toml edits** (no restart needed)
  ```bash
  gc reload
  ```

---

## Phase 10 — PR Lifecycle: Open to Merge

> Confirms the briefed PR/issue handoff path produces approved GitHub text before a human or verdict-executing agent performs the write.
> Run after Phase 8 briefed handoff verification smoke tests pass.

- [ ] **Run `pr-pipeline-briefed` for the real branch**
  ```bash
  gc sling hecke/gc.run-operator pr-pipeline-briefed --formula --var source_bead=<bead-id> --var brief_slug=<slug>
  ```
  Expected: formula composes a template-complete PR body from the current branch and recorded focused-test evidence, then files a decision brief. It does not push or open a PR.

- [ ] **Run `create-issue-briefed` when the GitHub write is a new issue**
  ```bash
  gc sling hecke/gc.run-operator create-issue-briefed --formula --var source_bead=<bead-id> --var brief_slug=<slug>
  ```
  Expected: formula drafts a template-complete issue body from the source bead and target repo template, then files a decision brief. It does not file the issue.

- [ ] **Push branch and open PR** (after the human adjudicator approves ship gate output)
  ```bash
  git push origin <branch>
  gh pr create --title "fix(#335): L-conjugation for SNF_DRIFT repair (m → L*m*L⁻¹)" --body "..."
  ```

- [ ] **Merge PR** (the human adjudicator merges in GitHub)

- [ ] **Close source bead**
  ```bash
  bd close he-hw5z4 --reason "PR merged; L-conjugation fix shipped"
  ```

- [ ] **Confirm convoy update**
  ```bash
  gc convoy status he-714x7   # he-hw5z4 closed → convoy member count should update (use `convoy status`, not `show`)
  bd show he-714x7
  ```

---

## Quick Reference

```bash
# Orders
gc order list                              # see all orders
gc order history <name> [--rig <rig>]      # when did it last run?
gc order run <name> [--rig <rig>]          # fire manually
gc order check                             # which are due now?

# Events
gc events --follow                         # live stream
gc events --type <type> --since 30m        # filter by type
gc events --watch --type brief.decided     # wait for next brief decision

# Sessions / workers
gc session list [--template <agent>]       # list sessions
gc session logs <session-id>               # what did a session do?
gc status                                  # pool states and counts

# Formulas
gc formula list | grep brief               # list brief formulas
gc formula show <name>                     # inspect a formula
gc formula version-check <bead-id>         # is running bead on current formula?

# Dispatch
gc sling <rig>/<agent> <formula> --formula        # explicit dispatch
gc sling <rig>/<agent> <formula> --formula --dry-run  # preview only
```
