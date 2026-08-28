# MathCity Dashboard — Screens

**What this is.** The views. Every screen reads off
[dashboard-object-model.md](./dashboard-object-model.md); layout data comes from
[dashboard-fixtures.md](./dashboard-fixtures.md).

**Style:** LMFDB. Clean, uncluttered, few headings, controllable. Density comes
from tables, not sectioning. Search is first-class. Server-rendered, no
JavaScript required, loopback only, desktop and mobile.

---

## The five primitives

Everything is one of these. A sixth requires justification.

| Primitive | Shape | For |
|---|---|---|
| **Spine** | Vertical timeline, durations between stops | Lifecycles |
| **DAG** | Layered graph, server-rendered SVG | Dependency structure |
| **Grid** | Rows × slots | Occupancy, and **absence** |
| **Bar** | One proportional bar, segmented | Progress, ratios, step state |
| **Strip** | Fixed-position cells, or a sparkline | Gates; quantity over time |

**Overlays, not new charts.** One DAG layout answers four questions by changing
what fills the nodes. The operator learns one picture and reads many measures.

**Honesty rules.** Color is never the only carrier · denominators always visible ·
absence renderable · probed values visually distinct from stored ones · a failed
probe never renders as a value · derived states show their inputs · **a check that
could not have failed must not render as a check that passed.**

---

## Screen 1 — The census (landing)

The answer to *what is the city doing*, and the proof it is doing it.

```
┌────────────────────────────────────────────────────────────────────┐
│  7 advancing · 45 open · 3 stalled · 1 stranded      [ search ]    │
│  ALIVE — 4 canaries fresh, last step closed 40s ago                │
├────────────────────────────────────────────────────────────────────┤
│  ▓▓▓▓▓▓░░░░  hecke      3/4 slots    ▓▓░░░░░░░░  gascity-packs 2/6 │
│  ░░░░░░░░░░  lmfdb      0/2          ▓▓▓▓░░░░░░  agent_skills  1/3 │
├────────────────────────────────────────────────────────────────────┤
│ MOLECULE   RIG      FORMULA        WHO     STEP BAR        WHY  AGE│
│ gsp-q31o…  gsp      build-basic…   brad-2  ▓▓▓▓▓▒░░░░      order 4h│
│ he-8kd2…   hecke    planning-…     creek   ▓▓▓░░░░░░░      human 12m│
│ …                                                                  │
├────────────────────────────────────────────────────────────────────┤
│ ▸ 38 open, not advancing        ▸ 12 ready, unclaimed              │
│ ▸ 4 blocked                     ▸ 7 deferred (on purpose)          │
├────────────────────────────────────────────────────────────────────┤
│ TICKER   16:42:11  step closed    gsp-q31ot8 · write-plan          │
│          16:41:55  claimed        he-8kd2 · decompose  ← by creek  │
│          16:40:02  order fired    tail-end-detector → 0 found      │
└────────────────────────────────────────────────────────────────────┘
```

**Four bands, top to bottom.**

**Band 1 — the headline.** `7 advancing / 45 open` is the health signal: if the
gap widens over days, work is piling up dead and you see it without reading a
row. Beside it, the liveness verdict — `ALIVE`, `IDLE`, `DEAD`, or `UNKNOWN` —
with its evidence inline, never a colored dot alone.

**Band 2 — the capacity grid.** Rows are rigs, cells are slots, filled or empty.
**A table shows presence; only a grid shows absence.** Empty cells are the point:
idle capacity is information, and a list of running things structurally cannot
display it. Clicking a rig goes to its page.

**Band 3 — the census.** One row per molecule, six columns answering
who/what/where/why/when/how. **All molecules are here** — `is_advancing` is a
column you sort and filter on, not a filter baked into the view. Default sort
puts advancing first.

**Band 4 — what is not running**, as collapsed counts. Each expands in place.
`deferred` is visually separated from the rest: deliberately-not-worked-on and
accidentally-not-worked-on must never look alike.

**The ticker sits at the bottom and is the proof of life.** Motion is the only
honest evidence that things work — a green tile is an assertion, things visibly
happening is evidence. Default tiers: alarm, milestone, progress. Chatter off.

**Silence is disambiguated by the canary line, not by the ticker.** A quiet ticker
plus fresh canaries reads `IDLE`. A quiet ticker plus stale canaries reads `DEAD`.
Without the canaries those are indistinguishable, which is the worst possible
ambiguity — the reassuring and catastrophic readings look identical.

---

## Screen 2 — Molecule

The compact step bar from the census, expanded.

```
gsp-q31ot8 · build-basic-briefed · gascity-packs            [advancing]

  now: implement · 4h 12m in this step · last motion 6m ago

  ▓▓▓▓▓▓▓▓│▓▓▓▓▓▓│▒▒▒▒▒▒▒▒▒▒▒▒│░░░░│░░░░│░░░░
  reqs     plan    implement    review finalize brief
                   ▲ you are here

  EVIDENCE (this step)
    D claimed          16:02  brad-2
    E agent active     16:38  transcript
    C commit           16:36  a4f2e1 "wire the resolver"
    B artifact         16:36  .gc-builds/gsp-q31ot8/impl-summary.md
    A step closed      —      not yet
                             └─ chain intact, work in progress
```

**The step bar.** Segments ordered by **dependency depth**, not declaration
order — a strictly linear bar would assert a serial history that didn't happen.
Steps in one layer are subdivided within one segment. Width equal per step
initially; later, width proportional to elapsed time, which turns the same bar
into a where-did-the-time-go picture with no new chart.

**Clicking without JavaScript.** Each segment is `<a href="#step-id">`; the step
detail blocks sit below and reveal via `:target`. On mobile the segments become
too small to hit, so the detail list below is the always-available fallback.

**The evidence chain is the diagnostic.** Five links in order — claimed, agent
active, commit, artifact, step closed — each with a timestamp and where it was
read from. **Where the chain breaks is where the problem is:**

| Reaches | Reads as |
|---|---|
| `claimed` only | Claimed, agent never came alive |
| `claimed, active` | Working, producing nothing yet |
| `…commit/artifact` | Healthy in flight |
| all five | Complete |

Below: the lifecycle **spine** (created → ready → claimed → … → landed) with the
duration between stops and **the longest gap marked**, because that gap answers
"why is this taking so long." The spine renders loops — re-dispatch, revise,
supersession — rather than asserting a linear history. Rows are *reached*,
*not yet*, *skipped with a reason*, or *repeated ×N*.

Then: worker, worktree, artifacts, cost, budget, `why` with its dispatch chain,
and the full DAG for molecules whose shape the bar flattens.

---

## Screen 3 — Rig

```
hecke                                          active · 3/4 slots

AGENTS        3 active · 1 idle · 0 limited
MOLECULES     2 advancing · 11 open · 1 stranded
QUEUE         12 ready · 4 blocked · 7 deferred · oldest 31d
WORKTREES     19 · 14 orphaned · 119.7 GB          ← click through
HEALTH        data plane healthy · dispatcher live
```

Five collapsed sections, each expanding to the relevant list. The rig page is a
router, not a report — it exists to get you to the object that matters.

---

## Screen 4 — Worktree browser

Requested directly: click a rig, see its worktrees, click one, see what happened
there.

```
PATH              BRANCH          BY       STEP        LAST      SIZE  STATE
he-kotqf          polecat/he-k…   creek    implement   14d ago   13 GB orphan
he-timtb          polecat/he-t…   brad-2   implement   9d ago    13 GB orphan
gsp-7l4loa        polecat/gsp-…   mutt     review      2h ago    41 MB active
```

**`BY` and `STEP` are the load-bearing columns** — a junk directory is only
actionable if you can trace it to the agent and step that made it. Sort by size
to find the disk, by age to find the junk, by agent to find a pattern.

`orphan` (no live session, no open bead) and `unregistered` (git no longer knows
it exists) are **separate flags** — different problems, different remedies.

The worktree page shows commits, the molecule and step it served, untracked files
flagged `harvestable`, and a stable `url` so the directory can be referenced in an
issue or sent to another agent.

**Junk accumulation is a trend, not a snapshot**: a strip of orphan count over
time sits at the top, because the number alone doesn't tell you whether cleanup
is keeping up.

---

## Screen 5 — Gates

A gate is a fixed-position cell in a fixed-order strip. **Position is meaning**,
so the strip becomes a fingerprint you learn to read at a glance — like a
barcode, not a checklist.

```
G1 G2 G3 G4 G5 G5b G6 G7 G8 G9 G10 G11 G12 G13 G14 G15 G16
▓  ▓  ·  ▓  ·  ·   ·  ▓  ▓  ▓  ·   ·   ·   ▓   ▓   ·   ▓     ← passed / NA
▓  ▓  ·  ✗  ·  ·   ·  ▓  ▓  ▓  ·   ·   ·   ▓   ▓   ·   ▓     ← G4 failed
```

Filled = passed, `·` = N/A with a reason, `✗` = failed. Because the order never
changes, a failure in position 4 is recognizable without reading a label, and two
artifacts with the same failure shape look the same. Click a cell for the
evidence, the rule it enforces, and its `policy_ref`.

Three places gates appear:

1. **On a molecule's terminal step** — did the output clear its gates.
2. **On a formula page** — which gates this formula's output fails, aggregated.
   This is the producer-quality signal.
3. **City-wide, as a pass-rate table** — and here the interesting reading is
   inverted: **a gate that never fails is suspect, not healthy.** A 100% pass rate
   across hundreds of artifacts means either the gate is perfect or it is not
   actually running, and the rate alone cannot distinguish them. Gates with zero
   failures over a long window are flagged for inspection.

---

## Screen 6 — Formula

The template DAG, with overlays. **One layout, four questions.**

```
[ failures ] [ duration ] [ cost ] [ tier ]        ← switch the fill

    reqs ──→ plan ──→ decompose ──┬─→ impl-a ─┐
                                  ├─→ impl-b ─┼─→ review → finalize → brief
                                  └─→ impl-c ─┘
                                      ▓▓▓▓ 14 failures here
```

Failure count as fill turns "failure rate" from a number into a **location** —
always-dies-at-step-5 is a fixable defect, dies-at-random is an environment
problem, and one rate cannot tell them apart. Tier as fill makes a high-tier model
on a mechanical step something you can *see*.

Alongside: invocations over time (strip), outcome mix (bar), rehearsal and
smoke-test status, and an `enabled` toggle wired to
`capacity.disable_formula()`.

---

## Screen 7 — Ticker

The full stream, filtered. Timestamp · tier · kind · subject (linked) · detail.
**Filters live in the URL** so a refresh does not reset them.

**Cause and response are shown paired**, indented under the cause. An order that
fired and produced nothing shows as a cause with no response — a visible break in
the chain, and far more informative than either event alone.

Retention is per tier: alarms are kept far longer than chatter.

Live updating is meta-refresh on the filtered view. No JavaScript.

---

## Screen 8 — Search and sort-by

One dataset, many groupings, **all simultaneously available**. Not seven screens —
seven `group_by` values over the same list.

```
work by:  [molecule] [agent] [rig] [order/event] [brief] [epic/convoy] [period]
```

Every object exposes `.url`, so every view is linkable, quotable in an issue, and
sendable to another agent.

---

## Finding what is stuck — the diagnostic path

The screens exist to make this one path short:

```
census → sort by state → stalled/stranded
   └→ molecule page → evidence chain → broken_at
        ├─ claimed, never active     → agent died at start   → agent page
        ├─ active, no output          → agent working blind   → transcript
        ├─ output, not closed         → completion not recorded
        └─ no claim at all            → dispatch never landed → why + order
```

**`broken_at` is the answer to "figure out the source of the problem."** Every
other screen is navigation toward it.

---

## Control — the dashboard is a web interface for the API

Every mutating `mctl` call has a form. The interaction is decided by the action's
**blast-radius tier**, not by the designer's taste.

| Tier | Interaction | Examples |
|---|---|---|
| **low** | One click, undo offered | nudge, set priority, run an order now |
| **medium** | Effect plan shown → confirm | set N(R), add agents, disable a formula, defer, redispatch |
| **high** | Effect plan **+ typed target name** | suspend a rig, cancel a molecule, close a session, stop the city |
| **gated** | **The dashboard does not do it** — it prepares the request and hands it to the existing gate | branch delete, worktree removal, push, merge, PR, tag, bead delete, kill-switch toggle |

**The `gated` tier is the one that matters.** Those operations already have a
human-approval gate that predates this dashboard. A button that performs them
directly is not a feature — it is a hole in an existing control. The dashboard
makes the request *easy to raise* and never satisfies it itself.

The live case: 14 frozen worktrees under an unrecoverable hazard. A "prune" button
is exactly how 119.7 GB disappears by accident.

**The no-JS constraint produces the safety flow for free.** A plain HTML form
POSTs, the server renders the effect plan, a second POST applies it. Preview-then-
confirm *is* the two-step form. No script, and the safety mechanism is the
mechanism you already had to build.

*(Low-tier actions stay one-step. Preview is proportionate to blast radius —
requiring confirmation to nudge a session would train the operator to click
through confirmations, which is how the high-tier ones stop working.)*

### Where controls live

Controls sit **on the object they act on**, never in a separate admin screen:

- **Census row** → nudge · redispatch · set priority
- **Molecule page** → cancel · retry step · redispatch
- **Rig page** → set N(R) · add agents · suspend · enable/disable formula
- **Agent page** → nudge · wake · reset · close slot
- **Order page** → run now · set interval · disable
- **Worktree page** → *request* removal (gated, never performed here)

### After the action

Every applied plan renders **before / after** on the spot — what changed, and
what the city looked like on each side. That is what makes *"watch how the city
responds when I add agents"* real rather than aspirational.

Control actions are **events**, so they appear in the ticker like anything else,
attributed to the dashboard. A change made from a browser is as traceable as one
made from a shell, and everyone watching sees it happen.

### The assumption underneath

**Loopback only.** The tiers above assume the interface is not routable and
therefore needs no authentication. **If that ever changes, every tier is void**
and an authorization model comes first. This assumption is load-bearing and
belongs wherever the interface is deployed.

---

## Knowls vs. expand/collapse

The distinction the whole interface hangs on, and it is a clean one:

| | **Knowl** | **Expand / collapse** |
|---|---|---|
| Contains | A **definition** | **More of this particular thing** |
| Same everywhere? | **Yes** — identical wherever the term appears | **No** — specific to this row, this moment |
| Example | "What is a convoy" | "Show the other 38 molecules" |
| Answers | *What does this word mean* | *Give me more data* |

**The test:** if the expanded content would be identical on every page where the
token appears, it is a knowl. If it depends on which row you clicked, it is a
disclosure.

**Knowls** — every term in the city vocabulary (molecule, convoy, epic, strand,
stall, drain, order, formula, rig, sling, step, gate, pool, `poolDesired`, claim,
lease, wisp, W/P state, unlock count), every diagnostic code, every rule ID, every
bead ID.

**And a knowl carries a live example.** *"A convoy is a group of beads that land
together. Example: `as-g6864` (2/5 closed)."* One click and you are looking at a
real one — which is how LMFDB teaches you what a newform is, and it works for the
same reason: you see it for yourself.

**Not knowls** — collapsed row groups, step detail blocks, evidence chains,
agent transcripts, commit lists, anything with an action attached.

**Two hard rules:**

1. **An unresolved token stays plain text.** A knowl that expands to nothing
   promises an explanation the dashboard does not have.
2. **Nothing actionable hides in a knowl.** Knowls are for learning, not for
   operating. If the operator needs it to act, it is on the page.

**Default collapsed:** the not-advancing bands, chatter, step details, agent
transcripts, commit lists, per-rig breakdowns, diagnostics marked non-actionable.
**Default open:** the headline, capacity grid, advancing census, ticker (three
tiers), alarms, and anything with `actionable=True`.

---

## Loading

Requested explicitly: *don't information dump; load things as needed*.

- The landing page fetches counts and the advancing rows. **Nothing else.**
- Collapsed sections fetch on expand.
- Bodies, transcripts, diffs, commit lists are never in a roster read.
- Counts never force materialization.
- Every list is paged, and **the page size is stated** — a truncated list says so
  rather than looking complete.

**A slow section degrades alone.** One rig that will not answer renders as a named
row with its reason while everything else loads. It never blocks the page, and it
never silently shrinks a total.
