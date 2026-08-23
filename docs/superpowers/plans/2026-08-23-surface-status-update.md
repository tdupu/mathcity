# SURFACE-STATUS.md Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> or `superpowers:executing-plans`. Steps use `- [ ]` for tracking.

**Goal:** bring `docs/SURFACE-STATUS.md` into agreement with what the tracker and `main`
now say, and add a section for MCP surfaces that are IN PROGRESS rather than done or absent.

**Architecture:** the ledger has two printed tables (§1 MCP commands, §2 Skills) and three
reference sections below a divider. This plan edits rows in place, adds one printed
section, and never changes the two-table print contract that `/surface-ledger` depends on.

**Spec:** the ledger's own rule, in its header —
*"every time an MCP tool is used, if it is not in this ledger, add it"* (Taylor, 2026-08-23).

## Global Constraints

- **`NOT PROBED` is load-bearing.** Never convert it to a blank, and never convert it to
  `WORKS` on the strength of a merge — only on an exercise in this city, naming the session.
- **A merged fix is not a probe.** `#176` merging means the DEFECT is fixed; it does not
  mean `city_health` was exercised. Rows change to `NOT PROBED (defect fixed, unexercised)`,
  not to `WORKS`.
- **`[measured]` vs `[inferred]` never blurred**, per the repo standard.
- **`tdupu/mathcity` is PUBLIC.** Sanitize: `<city-root>`, `<repos-root>`, `<home>`,
  `127.0.0.1:<port>`.
- **No `Co-Authored-By` trailers** (P5.5).
- The print contract: `/surface-ledger` prints **only** what is above the
  `# Reference — not printed` divider. A new printed section must go above it and must be
  worth printing every time.

---

## Task 1: Correct the six stale rows in §1

**Files:** Modify `docs/SURFACE-STATUS.md` §1.

Each row below is stale because a merge landed after the ledger was written. **Change the
status and the "What is broken" text; add the closing issue number to the GitHub column.**

- [ ] **Step 1: `city_health`** — currently `NOT PROBED` with *"S48 recorded it LIES —
      reported data_plane `unreachable`…"*

      New status: `NOT PROBED` (unchanged — it has not been exercised).
      New text: **the defect it names is fixed.** #176 and #159 merged 2026-08-23. It now
      probes each rig and reports three-valued; a rig it could not reach is a named row
      with a reason, excluded from the total explicitly, and `unknown` is never rendered
      as 0. **The S48 "it LIES" observation is historical, not current.**
      GitHub column: `#176 (closed), #159 (closed)`.

- [ ] **Step 2: `briefs_create`** — currently *"Four open defects filed against it — do not
      read as working."*

      New text: **two of the four are closed.** #169 (structural validation — `Gate
      Evidence` was unchecked at creation) and #173 (both halves: creation now REFUSES a
      sourceless brief, and an already-bricked brief is repaired) merged 2026-08-23.
      **#168 and #148 remain open.**
      GitHub column: `#169 (closed), #173 (closed), #168, #148`.

- [ ] **Step 3: `commission_brief`** — currently `NOT PROBED` citing duplicate briefs
      `mc-7po` and `mc-60j`.

      New text: **the tool now exists on the typed surface** — #190 core + registration
      merged 2026-08-23, taking the roster to 33. The duplicate-brief observation stands
      and `mc-7po` is deliberately **left open as #182 Q4's reproduction**, the way
      `he-wk44t4` is #173's. Do not close it.
      GitHub column: `#190 (closed)`.

- [ ] **Step 4: `work_dispatch`** — currently `NOT PROBED`.

      New status: **`DEGRADED`**. It was exercised — this is a real probe, not a merge.
      New text, `[measured]`:
      ```
      gc sling on a live bead    exit 0 at 162.7 s
      DISPATCH_TIMEOUT_SECONDS   120
      ```
      **The dispatch SUCCEEDED 43 seconds after mctl reported failure.** #184 merged, so
      a timed-out dispatch now reports `unknown` rather than *"no dispatch was recorded"* —
      the honest report, because a timed-out command may already have run. When disarmed
      it refuses cleanly with `MCTL_LIVE_DISPATCH_DISARMED`. Remaining defect: the 162.7 s
      is **`gc` startup tax, not work** — see Task 4.
      GitHub column: `#184 (closed), #182 (closed), #146 (closed), #160 (closed)`.

- [ ] **Step 5: ADD a `briefs_adjudicate` row** — it has no row at all.

      Status: `NOT PROBED` (defect fixed, unexercised).
      Text: `classify_tier` reads the adjudicator from **frontmatter**
      (`materialize_plan.py:294-297`) and the created brief document carried no frontmatter
      block, so an MCP-adjudicated brief could never reach `TIER_ADJUDICATED` — **the bead
      said decided while the document stayed silent.** #155 merged 2026-08-23; the
      frontmatter is now written. **Reproduced live on `mc-60j` during the #180 hand-run
      before the fix.**
      GitHub column: `#155 (closed)`.

- [ ] **Step 6: `fleet_sessions`** — currently `DECLINED`.

      Keep `DECLINED` — the probe was declined and that is a fact about the session, not
      the tool. **Add the answer that arrived another way**, `[measured]` 2026-08-23:
      ```
      tmux -L gt list-panes -a   ->  21 panes
        4 gc__run-operator · 3 mathcity__brief-operator · 8 core__control-dispatcher
      ```
      **The city uses a NAMED socket (`gt`).** A bare `tmux` invocation reads the default
      socket, finds nothing, and renders as *"no fleet"* — that reading was published
      roughly twenty times over sixteen hours before the socket was found. **The question
      `fleet_sessions` was proposed to answer has an answer; the tool still has not been
      exercised.**

- [ ] **Step 7: verify the print contract still holds**

      Run: `sed -n '1,/^# Reference/p' docs/SURFACE-STATUS.md`
      Expected: the two tables and nothing else. **If the new IN PROGRESS section (Task 2)
      is not inside this output, it will never print.**

## Task 2: Add the printed "IN PROGRESS" section

**Files:** Modify `docs/SURFACE-STATUS.md` — new §3, **above** the `# Reference` divider.

**Interfaces:** Produces a third printed table. `/surface-ledger` will print three tables
after this task, not two. **The header's own words — *"the two tables below, and nothing
else"* — must be updated in the same commit or the document contradicts itself.**

- [ ] **Step 1: Write the section**

```markdown
## 3. MCP surfaces IN PROGRESS

Neither live nor absent: named, scoped, and not yet on the surface. A surface here is
**not callable** — do not read a row as a tool.

| Surface | Issue | State | What exists | What is missing |
|---|---|---|---|---|
| `get_worker_pool_size` | **#197** | scoped | nothing | live seat count for a named pool. Must report **`unknown`, never 0**, when it cannot probe — a `0` here recreates the exact failure that produced twenty false "no fleet" reports. |
| `get_pools` | **#197** | scoped | nothing | the pool roster: `claim.pools`, `RouteTargets`, `poolDesired`. Must distinguish *a pool with zero seats* from *no such pool* — `mathcity` today is the second and reads as the first. |
| `get_sessions` | **#197** | scoped | nothing | live session beads per rig |
| `adjust_worker_pool` | **#197** | scoped | nothing | takes a **valid pool** and a number. Must **refuse an unknown pool by name**, never silently no-op. |
| `assign_molecule_to_pool` | **#182** (closed) | **PAUSED** | nothing | paused on measured grounds: `gc.routed_to` is stamped on every routable step **at cook time** by `ApplyGraphRouteBinding`, so a dispatch's steps are already addressed. hecke proved it — `he-e6cnz1` CLOSED 07:28 with worker `gc__run-operator-gt-9e1jpg`. **What was missing was never an assignment write.** |
| `assign_molecule_to_session` | **#182** (closed) | **PAUSED** | nothing | same pause. The explicit-target path; `he-81bo8` (`hecke/gc.implementation-worker`, a session bead) is the one working example in the city. |
| `standardize_github_issue` | **#185** | scoped | `create-issue` templates + `issue-investigation-standard.md` | the typed tool. **Do NOT build on `update-issue`** — #52 records it as Magma-package consolidation semantics, destructive on an agent-maintained tracker. |
| commission adapter (issue → claimable molecule) | **#179**, **#180** | proven by hand, not built | `create_issue_bead` + `commission_brief` + `commission-work-briefed.toml` | the adapter. Four of five steps proven by hand: `gh#1 → mc-7d0 → mc-60j → readiness "ready"`; step 5 refuses because **`mathcity` has no `gc.run-operator` pool.** |

**Two of these were named by the repo owner and lost in a closed issue.**
`adjust_worker_pool` and `get_worker_pool_size` were recorded on #182, which then merged
with the cook/sling half only and was closed on that partial scope. **#197 exists to hold
what #182 dropped** — that is why a closed issue appears in this table.
```

- [ ] **Step 2: Fix the header, same commit**

      The header says *"Displayed by `/surface-ledger` — **the two tables below, and
      nothing else**."* Change to **three tables** (§1 MCP commands, §2 Skills,
      §3 In progress).

- [ ] **Step 3: Verify the print contract**

      Run: `sed -n '1,/^# Reference/p' docs/SURFACE-STATUS.md | grep -c '^| '`
      Expected: rows from all three tables. **If §3 is below the divider it prints nothing.**

## Task 3: Add the missing gap rows in the Reference gaps table

**Files:** Modify `docs/SURFACE-STATUS.md`, "MCP surface gaps" table.

- [ ] **Step 1:** three existing gap rows carry no issue number — *"Generic bead
      read/write"*, *"Lifecycle (`gc start/stop/restart`)"*, *"In-progress-start
      visibility."* **Either file them or mark them `UNFILED` explicitly.** A gap with a
      blank GitHub cell is indistinguishable from one whose issue nobody looked up.

- [ ] **Step 2:** add a row: **`briefs_adjudicate` cannot be reached by its intended
      name** — #175 proposes renaming it `briefs_relay_adjudication` because the current
      name reads as a grant of authority it does not carry. **STOPPED, not abandoned** —
      the repo owner ruled it off-mission for the dogfood, and it stays filed.

## Task 4: Record the claim-window resolution where the ledger sends it

**Files:** `docs/GASCITY-ISSUES.md` (per the ledger's own scope note), plus a one-line
pointer from SURFACE-STATUS's Cross-cutting findings.

- [ ] **Step 1: Write the measurement**

```
mctl work ready   (the query itself)        11 ms
bd ready --limit 20                        142 ms
gc hook --help    (STARTUP ONLY, no work) 9,584 ms
```

**`gt-5j5c5p`'s premise — "work query (71s) exceeds 45s claim window" — is refuted. The
query is eleven milliseconds.** The window is consumed by `gc` starting up, six or seven
times over. That is #184's finding through a different door: *`gc` does ~8-10 s of
city-scoped work on every invocation, before it knows which subcommand it is running.*

**Nine open P0s describe this one defect.** Two were refuted by measurement
(`gt-murbwd` across six rigs; `gt-5j5c5p`'s premise). **The remedy is upstream in `gc`,
which is why it is recorded here and not in SURFACE-STATUS.**

- [ ] **Step 2:** add one line under SURFACE-STATUS's Cross-cutting findings pointing at
      it. **Do not duplicate the content** — the scope note exists to keep `gc` problems
      out of this file, and a summary here would drift from the original.

## Task 5: Resolve the location contradiction

**Files:** the file itself.

- [ ] **Step 1:** the header says *"Maintained in `tdupu/mathcity` (`docs/`)"*. `[measured]`:
      it exists at `<city-root>/mathcity/docs/SURFACE-STATUS.md` and **not** in
      `<repos-root>/mathcity/docs/`. **A ledger built to catch surfaces that do not match
      their documentation currently does not match its own.**

- [ ] **Step 2:** copy it to `<repos-root>/mathcity/docs/`, commit, and push — **or**
      change the header to say where it actually lives. **Either is correct; the current
      state is not.** The repos copy is preferred: this file is a public artifact and the
      tracker it describes is public.

## Task 6: Changelog

- [ ] **Step 1:** append, above the existing entries:

```markdown
- **2026-08-23 (lumby)** — six §1 rows corrected against merges that landed after the
  ledger was written (`city_health`, `briefs_create`, `commission_brief`, `work_dispatch`,
  new `briefs_adjudicate` row, `fleet_sessions` answered-by-other-means). Added **§3 MCP
  surfaces IN PROGRESS** — eight named-and-scoped surfaces that are neither live nor
  absent, including two the repo owner named that were lost when #182 closed on partial
  scope. Recorded that the file's stated home and its actual location disagree.
```

---

## Self-review

**Spec coverage.** The ledger's rule is *"every MCP tool used, if not in this ledger, add
it."* This plan adds one missing row (`briefs_adjudicate`), corrects five, and adds a
category the rule does not cover — **in-progress surfaces, which are used by nobody and
therefore never trip the rule.** That is a gap in the rule, not just the document.

**Placeholder scan.** No TBDs. Every row carries its issue number and its measurement.

**Consistency.** Status values used are exactly the five in the legend. **No row is
promoted to `WORKS` on the strength of a merge** — the legend requires an exercise, and
`work_dispatch` moves to `DEGRADED` only because it was genuinely exercised.

**One thing this plan does NOT do:** re-probe anything. Every correction is from a merge,
a tracker state, or a measurement already taken. **A row that says `NOT PROBED` still says
it afterwards** — because the honest fix for "not probed" is to probe it, and that is a
Mayor's job through the MCP, not an editor's.
