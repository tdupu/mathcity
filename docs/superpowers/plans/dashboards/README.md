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

## Implementation status — what is built vs. designed-not-built (as of origin/main 326083d, 2026-08-23)

### BRIEFS dashboard
**Works today:** the base adjudication surface renders (pile/stack/brief detail),
and the write-side plumbing the design needs largely landed 2026-08-23:
- `briefs_options` MCP tool is live; `BriefRecord.to_dict()` emits `body` +
  `sections` + `body_diagnostics` (the present-it body the detail screen reads).
- **#208** decision_options + recommendation **write path** — landed (Plan G,
  `326083d`); a recommendation stays advisory (brief deposits UNDECIDED).
- **#76** no_brainer field (Field 7) **write path** — landed (Plan G).
- **#209** revise-return **formula** — landed (Plan H); a revise verdict now
  auto re-deposits. Live end-to-end still pending.
- **#205** mayor_boot handoff read — fixed (Plan F). **#210 / #172** MCP
  serving-commit stamp + rebind — landed (Plan I).

**Designed, NOT built yet:**
- **#66** (keystone) — several of the 9 designed screens have no real data source.
- **#76** — brief attribute fields 1–6 (unlock_count, track, priority, form,
  gates, shape) and the **read/render side of options** (#76 Field 8): the
  disposition panel still shows "names no options" even though the brief now
  carries them and the adjudication reader sees them.
- **#68** the full 9-screen vertical-slice redesign · **#125** adjudicate-fast
  (save-in-place, auto-advance) · **#198** overview-vs-queue count mismatch ·
  **#175** rename briefs_adjudicate → briefs_relay_adjudication.

### CITY dashboard
**Works today:** the base city/overview and rig/order/molecule read views render.

**Designed, NOT built yet (the observability slices):**
- **#115** (keystone) evidence log + `step.expected_artifacts` · **#88** A–E
  evidence/derivation core + `molecule.state` · **#87** object-model gap analysis ·
  **#113** queue_status · **#118** costs_summary · **#120** worktrees_status.
- **#153** — five merged city-dashboard slices "render nowhere" (backend-only
  completion was counted as progress).

### Shared / serving both
- **#207** dashboard_status/dashboard_restart MCP tools · **#165** dead MCP child
  renders as an empty city · **#154** no teardown discipline. All OPEN.

## Where dashboard plans/designs go (the convention)

Dashboard **design docs, prototypes, and implementation plans** live **here**,
under `docs/superpowers/plans/dashboards/<city|briefs>/`. Do not scatter them into
`docs/`, `subdomains/dev/docs/`, or the `plans/` root. See the repo `AGENTS.md`
"Dashboards" section for the one-line rule.
