# Dashboards — the two of them, and what is built

There are **TWO distinct dashboards** in this project. They are rendered by **one
codebase** (`assets/scripts/mctl_dashboard/`, screens under `screens/`), which is
why they get confused. They are not the same thing and their design docs must not
be mixed. This folder is the single home for both designs; each has its own
subfolder here.

| | **CITY dashboard** | **BRIEFS dashboard** |
|---|---|---|
| Purpose | Operator **observability** — rigs, orders, molecules, pools, city health | **Adjudication** — present-it briefs awaiting a human verdict |
| Audience | Operator watching the city run | Human adjudicator (Taylor / clerk) deciding briefs |
| Design here | [`city/`](./city/) | [`briefs/`](./briefs/) |
| Screens | overview / rig status / orders / molecules / evidence / costs / worktrees | pile / stack / deferred / adjudicated / the 7-section present-it brief |
| Code | `mctl_dashboard/screens/city.py`, `orders.py`, `pipeline.py`, `stack.py` | `mctl_dashboard/screens/brief.py`, `panel.py`, `render.py`, `app.py` |
| Naming | canonical name **city dashboard**. "mathcity dashboard" / "mctl dashboard" are the SAME thing — do not coin a third name | canonical name **briefs dashboard** (a.k.a. "Brief Manager") |

Both serve over stdlib `http.server`, server-rendered HTML, no build step, works
with JavaScript off. Data arrives over `mctl` MCP tool calls, never shell.

## Canonical design per dashboard

- **City:** [`city/`](./city/) — `HANDOFF.md`, `README.md`, and the
  `prototype/city-dashboard.dc.html` Claude-design prototype. This is the single
  city-dashboard design home (it previously lived at `docs/city-dashboard/`; moved
  here 2026-08-23 to sit beside the briefs design).
- **Briefs:** [`briefs/`](./briefs/) — `design_handoff_brief_manager/` (the latest
  Claude-design "Brief Manager" handoff, session 1) plus
  `2026-08-19-briefs-dashboard-redesign.md` (the vertical-slice implementation
  plan). An **older** briefs design at
  `subdomains/dev/docs/plans/mcp/claude-design-briefs-dashboard-2026-08-19/` was
  **retired and removed 2026-08-24**, superseded by `design_handoff_brief_manager/`.
  The Brief Manager design is now the only briefs-dashboard design — there is no
  second one to confuse it with.

## Implementation status — build state vs. issue state

**Verified 2026-08-28 against `main` and the running dashboard.** Supersedes
the `326083d` (2026-08-23) snapshot, which had drifted in *both* directions.

**Read these as two different facts.** A closed issue does not mean the thing
renders, and an open issue does not mean the code is missing — several issues
below stay open for follow-up while their code landed. Merging the two claims
into one is the exact error [#153](https://github.com/tdupu/mathcity/issues/153)
was filed to name, so this table keeps them apart.

### Routes actually registered (`app.py`)

```
/adjudicated /apply /briefs /city /deferred /diagnostics /junk /malformed
/molecules /orders /pile /preview /priority /queue /trace /validate /work
```

**There is no `/overview`, `/rigs`, `/costs`, `/worktrees` or `/evidence`
route, and their absence is not a missing feature.** Costs, worktrees,
queue-status and evidence are **panels inside `/city`**. Probing for them as
routes returns 404 and has already been misread once as "designed-not-built";
check `/city`'s panels before concluding a slice is unbuilt.

### CITY dashboard

`/city` renders (HTTP 200, ~199 KB) with these panels carrying real data:
City health (18 rigs) · Gates (5) · Blast radius (7) · Worktrees (188) ·
Queue Status · Costs Summary · Events List · Agents.

- **#153 — closing condition MET, recommend closing.** It asserts "no page
  consumes any of them" and "there is no city-operations surface". Both are
  now false: all five slices (#110 blast_radius, #112 fleet_sessions,
  #114 city_health, #116 events_list, #119 gates_status) are reachable and
  rendering on `/city`.
- **#120 worktrees_status — open, but the panel renders 188 rows.** Verify
  against its acceptance criteria, then close.
- **#113 queue_status · #118 costs_summary · #87 gap analysis · #66 keystone
  — CLOSED and rendering.** The previous revision listed all four as
  designed-not-built.
- Still genuinely open: **#115** evidence log + `step.expected_artifacts` ·
  **#88** A–E evidence/derivation core.
- The **Agents** panel currently reads *"Fleet size is unknown. The probe did
  not answer, so this is not a count of zero."* That is P6.2 working, not a
  defect — an unanswered probe reported as unknown rather than a plausible
  zero. Likely lock contention; see `mc-znfnm`.

### BRIEFS dashboard

Base adjudication surface renders (pile/stack/brief detail).

- **Code landed, issue still open** (do not read these as missing):
  **#208** decision_options + recommendation write path is in `mcp_server.py`;
  **#175** the rename is done — the tool is `briefs_relay_adjudication`.
  Also open: **#205**, **#209**.
- Genuinely open: **#68** 9-screen vertical slice · **#76** brief attribute
  fields 1–6 and the read/render side of options · **#125** adjudicate-fast ·
  **#198** overview-vs-queue count mismatch.

### Shared / serving both

- **#207, #165, #154 are CLOSED.** The previous revision called them "All
  OPEN"; the dashboard lifecycle verbs, MCP child health-check and teardown
  discipline all shipped. **#164** and **#172** are closed too; **#210**
  remains open.
- **Open, P1, not yet fixed:** `mc-znfnm` — every MCP call serializes on one
  process-wide lock over a single pipe, so one slow page blocks every
  concurrent request (measured: `/queue` 1.7 s alone, **64.9 s** during
  `/city`). This makes *every* latency figure in these docs conditional on
  what else was in flight — treat historical timings for `/city` (3.6 s,
  24.7 s, 61 s, "never") as measurements of concurrency, not of the route.

## Where dashboard plans/designs go (the convention)

Dashboard **design docs, prototypes, and implementation plans** live **here**,
under `docs/superpowers/plans/dashboards/<city|briefs>/`. Do not scatter them into
`docs/`, `subdomains/dev/docs/`, or the `plans/` root. See the repo `AGENTS.md`
"Dashboards" section for the one-line rule.
