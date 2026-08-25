# Dashboard Fleet — Execution Progress (live, resume-from-this-file)

> Sole writer: BART (repo-side, session 4270675a). Kept OUT of commits (lives in ~/gt).
> Base: origin/main (tdupu/mathcity) = **4d12140** at fleet launch (2026-08-24).
> Goal: get ALL dashboard issues implemented + tested (Taylor). Then Taylor does the
> Claude-design pass on the finished implementation (design AFTER implementation).
> PERT source: ~/gt/mathcity/docs/{DASHBOARD-STATUS,BRIEFS-DASHBOARD-STATUS,MATHCITY-DASHBOARD-STATUS}.md (QUIMBY S51).

## Fleet structure — 3 dependency-coherent cluster-forks, each spawning sub-subagents
Worktree root: `…/scratchpad/dash-worktrees/`. All off 4d12140.

| Cluster | Worktree/Branch | Scope (PERT order) | Status |
|---|---|---|---|
| **CITY** | `dash-worktrees/city` · `dash-city` | #87 (gap analysis, FIRST) → #115 (keystone) → #113/#118/#120 slices | running |
| **BRIEFS** | `dash-worktrees/briefs` · `dash-briefs` | #66 → #76 → #208p3 → #68 → #125 | PARTIAL — parked early, resumed. Committed: #76 Field 8 (**082f74e**, options render verified live), #208p3 body composer full-form (**fc1c591**). #125 staged (autofocus advance). **#66 + #68 NOT yet reported — resumed to account for them.** |
| **OPS** | `dash-worktrees/ops` · `dash-ops` | #165 · #207 · #154 · #162 · #198 · #172 (VERIFY only) | running |

## BART-owned (not in a fork)
- **#88** vs #115 read — DONE. VERDICT: narrow-not-close. #115 subsumes #88's evidence-chain half (A–E log + expected_artifacts + derived is_complete). #88's UNIQUE piece = `molecule.state` 5-value classification (advancing/stalled/stranded/dormant/complete, stranded-vs-dormant). Recommend: retitle #88 → molecule.state only, depend on #115. Reported to QUIMBY; issue-edit pending Taylor/QUIMBY confirm. Could fold molecule.state into the CITY cluster after #115.
- **#172 close** — after OPS fork verifies (issue-close is gated).
- **#186** — deferred (blocked on external #179/#180/#185).

## Landing discipline (Taylor: careful merging + cleanup + testing)
- Each cluster hands me its branch (many per-issue commits). I land ONE cluster at a time onto main, resolving the shared-file unions (mcp_server.py, diagnostics.toml, the six rosters, schemas.py) with keep-both — the A–I proven pattern.
- After each cluster lands: full `pytest tests/mctl` on the combined tree BEFORE the gated push.
- Remove each worktree + delete its branch after it lands.
- Every push gates through Taylor (authorize-git-operation).

## DESIGN DIRECTION (Taylor, 2026-08-24): dashboards must LOOK LIKE the .dc.html prototypes
- Briefs → `~/Downloads/plans/briefs-dashboard/design_handoff_brief_manager/Brief Manager Dashboard.dc.html`
- City → `~/Downloads/plans/mathcity-dashboard/prototype/city-dashboard.dc.html`
- So #68 = BUILD the visual fidelity (not defer to a later design pass). Restore the FIXTURES·NOT-LIVE-DATA badge (DRIFT flag). F33: counts derive from queries, no literals.
- VISUAL-FIDELITY forks: **briefs-visual LAUNCHED** (dash-briefs-visual @ 5472947, porting Brief Manager look into render.py/screens). **city-visual** to launch AFTER the city functional cluster lands (both touch render.py — avoid the collision).

## Landing ledger
| When | Cluster | origin/main | Notes |
|---|---|---|---|
| ~fleet | BRIEFS functional | **5472947** | #76 options render + #208p3 composer + #125 partial. #66 verified. FF, 1334. |
| ~fleet | OPS | **0c85901** | #165 respawn · #207 lifecycle tools (roster 36→38) · #154 teardown (+AGENTS.md) · #162 roster→live · #198 count fix. #172 VERIFIED + CLOSED. Clean merge, 1365 passed. |
| ~fleet | BRIEFS visual (#68) | **6257295** | Briefs dashboard MATCHES Brief Manager prototype: fonts embedded (data: URIs), §4 click-to-adopt, triage row actions, FIXTURES badge. 4 files +448/-32, clean merge, 1383 passed. (base already carried most of the token system/stoplight/detail — this closed the gaps.) Non-matches: `resolve→` gated on #66 kind data; empty-brief = `send back→`/revise per Taylor's standing rule. |

## PHASE 2 — ADR 0001/0004 rework (Taylor S51 rulings, hold lifted 2026-08-24)
Split with QUIMBY: **dashboard = me** (panel v2, city functional, city visual); **backend = QUIMBY fleet** (full-form gate minting in required-sections.toml, producer full-form passes + retire present-it --compact / catch-no-brainer compact-eligibility [no_brainer flag survives], backend-match audit, cancel-order). Legacy ~170 grandfathered.
- **ADRs committed locally**: docs/adr/0001-always-full-form-briefs + 0004-verdict-panel-spec (renumbered from city-side 0002; 0003 was retired-store-beads). Bundle with panel-v2 push. 1 ahead of origin.
- **PANEL V2 fork** (dash-panel-v2 @ 6257295): option-major REC/OTHER, click-to-adopt fills, one-click Submit + passive dry-run (two-step OUT), defer stays + verdict hints, error-briefs→rejection.json, HELD from briefs_options enabled/disabled_reason, PILE read-only row, fake chips dropped, browser-local Save. ZERO new backend. RUNNING. ⚠️ briefs_options never probed live — runtime surprises = findings, not code-arounds (relayed).
- **CITY functional** RESUMED (post-529): #87 done c0ae11c, finishing #115→#113/#118/#120 (dash-city @ 0e6afdc).

| ~fleet | CITY functional + ADRs | **b1f789f** | #87 gap-analysis · #115 keystone (/molecules routes, is_complete from declared artifacts) · #113 queue_status · #118 costs · #120 worktrees. + ADR 0001/0004. Merge conflicts resolved (family union + tool count→41). 1508 passed. #88 molecule.state UNBUILT (4/5 evidence links have no emitter — P6.2). |

| ~fleet | PANEL v2 (ADR 0004) | **231a981** | Option-major REC/OTHER (approve never blocked) · one-click Submit + passive dry-run · defer=4th verdict→briefs_defer · HELD/malformed re-grounded on briefs_options enabled/disabled_reason · fake chips dropped · browser-local Save. ZERO new backend. Clean merge, 1525 passed. **2 backend gaps → QUIMBY fleet**: (a) error-briefs view needs TYPED reader for .pile/.rejected/<slug>/rejection.json + pile gate-state (on-disk shape matches ADR; no MCP tool exposes it — left as honest banner, NOT a file read that breaks read-only-via-MCP); (b) atomic submit would touch /preview→/apply mutation-safety protocol (kept preview-first at route level). |

| ~fleet | CITY visual port (#68/#153) | **624de2f** | Stoplight pills (from single STOP scale, no new hex) · per-slot capacity strip · .ntdata metric tables · Cormorant/Lora fonts · FIXTURES badge. Applied prototype's shared visual language to backend-supplied data only. Clean merge, 1538 passed. P6.2 held (unknown/probe-failed → neutral). **2 scope-gaps flagged (not built)**: (a) distinct city chrome (masthead/sidebar/event-feed) needs a shared-shell split touching briefs surface — separate brief; (b) rich object-browser panels (census, tokens sparkline, N(R), agents table, gate board, canaries) have no backend data source — left as honest #116 placeholders. |

## ✅ DASHBOARD IMPLEMENTATION COMPLETE (2026-08-24)
All clusters landed on origin/main @ **624de2f**: briefs functional (5472947) + visual (6257295) + panel-v2/ADR 0004 (231a981); city functional+ADRs (b1f789f) + visual (624de2f). Ready for Taylor's Claude-design pass on the finished implementation. Remaining backend gaps routed to QUIMBY fleet (briefs_pile_state #226; molecule.state #88 emitters). #227 corrected (sanitized comment posted — dispatcher IS up, real cause = brief-operator pre_start timeout; fix owned by [b43111]).

## Fork status
- CITY functional: RUNNING (resumed) — #87 done c0ae11c, #115 finalizing, #113/#118/#120 pending.
- OPS: RUNNING — no report yet.
- BRIEFS functional: ✅ LANDED (5472947). #68-visual + #125-flow → visual fork.
- BRIEFS-VISUAL: RUNNING (just launched).
- gascity#32: ✅ code done (91892dac2), deploy bundle pending Taylor's gate.

## Anomalies (→ QUIMBY dogfood)
_none yet_

## Parallel (not this fleet) — GASCITY DEPLOY BUNDLE ready (Taylor-gated rebuild+restart)
Three gascity-fork branches ready to bundle into ONE rebuild (one restart, three fixes):
- **#32** gc emit fast-path: `fix/gc-event-emit-startup @ 91892dac2` (3 files +75/-7). Root cause: PackContentHashRecursive sha256's every pack file across 17 rigs on every config load; only the supervisor reads that snapshot. Fix: LoadOptions.SkipRevisionSnapshot for one-shot CLI loaders. MEASURED 7.3s→0.53s. #32 comment posted (option-B recorded). ⚠️ one flaky reconciler injected-failure test in a broad combined run (post-crash CPU thrash, didn't repro split) — do a CLEAN full `go test ./cmd/gc/` at deploy.
- **#99** pool pressure: `plan-b-pool-pressure @ c608add0a`.
- **#29** cherry-pick `a48bce497` onto the deployed fork lineage.
Deploy = assemble onto fork lineage → rebuild gc → restart city. Taylor-gated + city-side; the city is mid-bring-up after the 00:17 crash, so TIMING is Taylor's. Not prepped by BART yet (awaiting his go).
- restart6h ARMED in launchctl (~06:17) — disarm is Taylor-gated, city-side; flagged to Taylor.
