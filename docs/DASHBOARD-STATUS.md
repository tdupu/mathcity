# Dashboard Status — INDEX

> Split into two parts (Taylor, 2026-08-23; BART concurred with corrections):
>
> - **[BRIEFS-DASHBOARD-STATUS.md](./BRIEFS-DASHBOARD-STATUS.md)** — the adjudication surface
>   (:8491): #68 #66 #76 #208 #125 #140 #198 #186 + ops #207 #165 #154 #172 #162.
> - **[MATHCITY-DASHBOARD-STATUS.md](./MATHCITY-DASHBOARD-STATUS.md)** — the city observability
>   slices (HANDOFF design): #87 #115 #113 #118 #120 #88 #153 + closed slices.
>
> Issue rosters live in the two parts; implementation status is canonical in BART's
> `docs/superpowers/plans/dashboards/README.md`. THIS file keeps the one cross-dashboard
> coordination view: the unified PERT below.

## The unified PERT (S51 planning agent, 2026-08-23; corrections folded)

**Critical path to "Taylor adjudicates briefs on a fully-rendering dashboard":**
**#208 p3 → #76 (fields + options render) → #68 adjudication/stack screens → #125 (auto-advance) → #153 verified live**, with **#165 as a parallel gate** (a dead MCP child renders a finished dashboard as an empty city). Second limb: #66 Tier-2 remainder → #68 slice 5.

**Waves (≤4/wave, ranked by unlock count; dogfood each through bead → brief → verdict → typed dispatch):**

| Wave | Nodes | Status notes |
|---|---|---|
| 1 | **#87** (unlocks 4) · **#207** (3) · **#165** (2, goal-gating) · **#208 p3** (3, on Taylor's design edit) | briefs deposited S51 (mc-bavv/mc-5ncp/mc-bmmr — revised on format, returning via #209); #208p3 brief mc-ti9j same state |
| 2 | **#76** · **#66** remainder (Tier 1 mostly DONE per BART) · **#115** (keystone, after #87) · **#154** (after #207) | |
| 3 | **#68** remainder · **#125** · **#113** · ~~#172~~ **CLOSEABLE** (Plan I implemented it — BART, measured) | |
| 4 | **#140** · **#198** (re-measure first) · **#118** · **#120** (· #162 anytime — counts all stale) | |
| parked | **#88** (≈#115, side-by-side read pending) · **#186** (external deps #179/#180/#185 absent) | |

**Stale-premise flags, measured status:** #66 Tier 1 mostly done ✓(BART) · #172 fully implemented ✓(BART) → closeable · #68 premise wrong on both numbers ✓(BART: 36 tools, ALLOWED_TOOLS deliberate subset) · #88≈#115 needs body read (BART offered) · #198 re-measure on current main.
