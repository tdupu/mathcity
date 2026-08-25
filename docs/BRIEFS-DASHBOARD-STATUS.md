# Briefs-Dashboard Status — the adjudication surface (:8491)

> Part 1 of the dashboard census (Taylor's split, 2026-08-23; BART concurred with corrections).
> Part 2: [MATHCITY-DASHBOARD-STATUS.md](./MATHCITY-DASHBOARD-STATUS.md). Index:
> [DASHBOARD-STATUS.md](./DASHBOARD-STATUS.md). Companion rules: [SURFACE-STATUS.md](./SURFACE-STATUS.md).
> **#153's rule attaches to every row: done = renders in the served dashboard.**
>
> **Division of authority (BART 6689255, 2026-08-23):** IMPLEMENTATION STATUS (built vs
> designed-not-built) is canonical in `docs/superpowers/plans/dashboards/README.md` — defer to
> it on any disagreement. THIS file carries the coordination layer only: PERT, waves,
> critical path, dependency ordering.

## Issues

| # | State | What | PERT deps | Unlocks |
|---|---|---|---|---|
| 41 | CLOSED | original: CLI MCP + dashboard control plane | — | — |
| 68 | OPEN | FE umbrella: 9-screen redesign in vertical slices. ⚠️ premise DOUBLY stale (BART, measured @326083d): live roster is 36 ToolSpecs not 16/33, and `ALLOWED_TOOLS` (client.py:54) is a DELIBERATE hand-curated subset (client.py:9) — "should equal roster" is wrong by design | #66, #76+#208 | 2 |
| 66 | OPEN | backend core read/preview surface. ⚠️ Tier 1 mostly DONE (BART, measured): `briefs_options` live (mcp_server @672/@1700), `BriefRecord.to_dict()` emits body+sections+body_diagnostics (briefs.py:327-329). Re-verify the 12-item table row-by-row; remaining scope is Tier 2/3. **Dependency fan-in (keep visible, BART):** #67, #175, #72/#95/#102, #65/#58, #163 — data-layer deps the adjudicated/pending views need to be honest | fan-in above | 2 |
| 76 | OPEN | 7 brief attribute fields incl. options render (Field 8) — why G briefs show "NAMES NO OPTIONS" | #208 | 3 |
| 208 | OPEN | typed options/recommendation write path — parts 1–2 LANDED 326083d; **part 3 (body composer) held for Taylor's design edit to BRIEF-SYSTEM-REWORK-STATE-2026-08-19.md** | Taylor's edit | 3 |
| 125 | OPEN | adjudicate fast — save in place, auto-advance | #76 | 1 (the goal) |
| 140 | OPEN | held-back set counted but not reachable | queue view | 0 |
| 198 | OPEN | overview pending 174 ≠ /queue 173 — re-measure on current main before dispatch | — | 0 |
| 186 | OPEN | tracker view (issues × beads × briefs + actions). Family CONFIRMED briefs/intake (BART: operates on issues/beads/briefs, the operator surface for #180's loop) | #179/#180/#185 (external, absent) | 0 |

## Ops / lifecycle (serves both dashboards; homed here — all arose from this instance)

| # | State | What | PERT deps | Unlocks |
|---|---|---|---|---|
| 207 | OPEN | typed dashboard_status/dashboard_restart (reads #164 stamp) | #164 (landed) | 3 |
| 165 | OPEN | MCP child never health-checked — dead child renders as EMPTY CITY. **Parallel gate on the critical path** | — | 2 |
| 154 | OPEN | no teardown — debug servers run forever (tonight's duplicate instance) | #207 | 0 |
| 172 | OPEN→**CLOSEABLE** | MCP-serve staleness self-report — **FULLY IMPLEMENTED by Plan I** (BART, measured: serving.py SERVING_COMMIT at import; `_serving_meta` rides initialize + tools/list; da74d4b/097031d). Distinct surface from #164 (dashboard half). Verify vs its MRE, then close | — | — |
| 162 | OPEN | stale tool roster — every NUMBER stale (now 36 tools); defect class persists | — | 0 |

## Critical path (PERT, S51)

**#208 part 3 → #76 → #68 adjudication/stack screens → #125 → #153 verified live**, with **#165 as
a parallel gate**. Second limb: #66 Tier-2 remainder → #68 slice 5.

Wave 1 (dep-free, by unlock count): **#207** (3) · **#165** (2) · **#208 p3** (3, on Taylor's edit).
(#87 leads the MATHCITY file's wave 1.)
