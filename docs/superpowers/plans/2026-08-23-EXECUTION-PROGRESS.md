# Surface §4 Plans — Execution Progress (live, resume-from-this-file)

> Sole writer: BART (repo-side, session 4270675a). Updated AS execution proceeds so any
> restart (BART / QUIMBY / machine) resumes from here, not from memory. NOT committed to any
> repo (lives in ~/gt; LP1 bars git ops in ~/gt, not file writes).
> Base: origin/main (tdupu/mathcity) = **8c8a0ee** at fork start. gascity fork = **fd3508049**.
> Merge order (per QUIMBY): A → C → B2 → D3, unions resolved identically each time.

_Last update: 2026-08-23 20:47 EDT — A/B/C/D launched (running); E/F launching. #181→D, #206→A._

## Assignments / deconflicts
- **#181** (dispatch budget) → **Plan D** (first taker; my D-subagent holds it). Plan F does NOT do #181.
- **#206** (create_issue_bead priority) → ALREADY SHIPPED on main (commit 3e40e87 / main 8c8a0ee: `_priority_from_labels` in effects.py + 4 tests). Plan A Task 2 EXTRACTS/REUSES it for create_defect_bead and cites #206. Not a new subagent.
- **Plan E bug 1** (#73, brief-record-decision.toml $PACK_DIR) → HELD (Taylor unruled). E-subagent does bug 2 only.

## Worktrees (for restart find/clean)
| Plan | Repo | Path | Branch | Base SHA |
|---|---|---|---|---|
| A | mathcity | `…/scratchpad/plan-worktrees/plan-a` | `plan-a-intake` | 8c8a0ee |
| B | gascity | `…/scratchpad/plan-worktrees/plan-b` | `plan-b-pool-pressure` | fd3508049 |
| C | mathcity | `…/scratchpad/plan-worktrees/plan-c` | `plan-c-events` | 8c8a0ee |
| D | mathcity | `…/scratchpad/plan-worktrees/plan-d` | `plan-d-adapter` | 8c8a0ee |
| E | mathcity | `…/scratchpad/plan-worktrees/plan-e` | `plan-e-drain` | 8c8a0ee |
| F | mathcity | `…/scratchpad/plan-worktrees/plan-f` | `plan-f-instruments` | 8c8a0ee |

(full path root: `/private/tmp/claude-501/-Users-<home-user>-repos/4270675a-b833-4bd7-96c1-ad269ac329c6/scratchpad/plan-worktrees`)

---

## Plan A — mctl intake surfaces (#185) · mathcity · UNGATED, full
**Subagent:** launching. **Branch:** plan-a-intake. **SHAs:** none yet.
- [ ] Task 1: GitHub write layer + `create_github_issue` (MGHW_* codes, 6 rosters, served-schema test)
- [ ] Task 2: `create_defect_bead` + shared priority mapper
- [ ] Task 3: `standardize_github_issue` (additive-only, #52)
**PREMISE CORRECTION (BART):** create_issue_bead priority mapping is ALREADY FIXED and pushed
(`8c8a0ee`; `_priority_from_labels` in `effects.py`, 4 tests). Task 2 must EXTRACT/REUSE that
existing mapper for create_defect_bead — do NOT re-implement or re-fix create_issue_bead.
**Resume here:** await subagent RED/GREEN reports.

## Plan B — pool pressure #99 (Phase 1 only) · gascity fork · Go
**Subagent:** launching. **Branch:** plan-b-pool-pressure. **SHAs:** none yet.
- [ ] Phase 1 Step 1–4: failing Go test → readyBacklogTerm in `cmd/gc/city_runtime.go` → GREEN
- [ ] Phase 1 Step 5: commit on fork branch, hand to BART (rebuild+#29 cherry-pick = later gated deploy)
- [~] Phase 1 Step 6 (live) + Phase 2 (mctl pool tools): PARKED (city-up + Taylor restart gate)
**Resume here:** await Go test RED/GREEN.

## Plan C — mctl event participation (#202) · mathcity · code only
**Subagent:** launching. **Branch:** plan-c-events. **SHAs:** none yet.
- [ ] Task 1: `gc_events.py` emitter (copy the exact emit command from `formulas/brief-prep.toml`)
- [ ] Task 2: wire `briefs_create` → brief.submitted (dry_run emits zero; #188 precedent)
- [ ] Task 3: wire `briefs_adjudicate` → brief.decided (payload carries verdict + adjudicated_by)
- [~] Task 4: live acceptance — PARKED behind #204 unlatch + city-up
**Resume here:** await emitter RED/GREEN.

## Plan D — commission adapter (#179/#180) · mathcity · Task 1 + #181
**Subagent:** launching. **Branch:** plan-d-adapter. **SHAs:** none yet.
- [ ] Task 1: #192 — one error boundary per commission create (`commission.py`)
- [ ] #181: dispatch budget fix (work_dispatch 162.7s vs 120s budget) — D's feeder
- [~] Task 2 (hand-lap) + Task 3 (`commission_from_issue` wrap): PARKED behind B-deployed + #181-landed
**Resume here:** await #192 + #181 RED/GREEN.

## Plan E — drain formula repair (#73) · mathcity · ✅ DONE (already on main) — NO GATE
**Subagent:** COMPLETE (P5.4 stale-premise catch). **Branch:** deleted (was 8c8a0ee, no edits). Worktree removed.
- [x] Task 1 (bug 2): ALREADY FIXED on main by **2adc84b** ("formulas: two agent-executed paths that resolve to nothing", Aug 20, "Closes #73"; ancestor of 8c8a0ee). brief-shuffle-fast-drain.toml:65/67 carry the `<mathcity-pack-root>` form. Resolution test = Test 37 in tests/brief-no-brainer-arming/test_no_brainer_arming.sh (41/41), RED/GREEN re-verified by subagent.
- [x] Task 2 (bug 1): ALSO already fixed by 2adc84b — brief-record-decision.toml:209 has the pack-root form + "Do NOT $PACK_DIR" warning. **HELD-for-ruling is MOOT on the code** (the commit measured the stack-index impact null before shipping: 0 archived rows listed). If Taylor still wants a ruling it's about code already in main, not a pending edit.
**Anomaly (→ dogfood):** Plan E authored 2026-08-23 against a premise invalidated 2026-08-20 (#73 closed by 2adc84b). §4 census needs reconcile vs `git log --grep=#73`. Affects Plan C's live-acceptance premise (the fast-drain firing it predicts is already enabled).
**Resume here:** nothing — closed as already-satisfied. No commit, no gate.

## Plan F — instrument fixes (#205 only) · mathcity · ✅ CODE DONE — GATE PENDING
**Subagent:** COMPLETE. **Branch:** plan-f-instruments @ **86ac780** (clean FF onto 8c8a0ee, no conflict). Worktree kept until landed.
- [x] Task 2: #205 mayor_boot handoff honesty — ROOT CAUSE: boot_state read the per-rig store; handoff beads live in the HQ store (ctx.city_root). Fixed via `_hq_store_root`. Filter ruled out (gt-iw0dc3 matches). Added `MMAY_HANDOFFS_NOT_FOUND` (WARN, P6.2) + registered + CODE_PATTERN. 2 tests RED→GREEN in test_mayor_reads.py. Full suite **1250 passed**.
- [x] Task 1 (#181): NOT in F — Plan D owns it. Confirmed untouched (4 files only, no work.py).
**Anomaly (→ dogfood):** no #203-style served-schema e2e test exists for mayor_boot (only mayor_city_state/mayor_conservation). New diagnostic validates via generic response_schema; snapshot tests green. Small coverage gap — follow-up.
**Resume here:** present push gate for 86ac780 (clean FF). Then remove worktree + branch.

---

## QUIMBY 50 → 51 handoff (signed off, awaiting Taylor's restart)
Handoff bead **gt-d3arow** (run-log S50.md, catalog, PROMPT for QUIMBY 51). QUIMBY 51 boots on a server @ 326083d (carries tonight's code) and its mayor_boot will find gt-d3arow via Plan F (#205 HQ-store fix — live validation). Reconnect to the new session via ListAgents.
Threads carried to QUIMBY 51 (I'm holding same):
- dispatch retry: trace a770801e, convoy mc-yn4e adoption check
- rig-scoped drain verdict: watch seq > 6290176 (round-robin 4/tick; patience = measurement)
- gs-1vtf successor via G options
- Plan B gascity deploy: after drain observation, + #29 bundle, Taylor's restart gate
- 44 blockers self-draining? 2nd data point: mc-quq also closed on its own (gt-qb3i4o was 1st) — sweep may be moot
- G Part 3 (body composer) held for Taylor's design edit; options read/render side = #76 Field 8 (separate)

## Landing ledger (gated pushes)
| When | Plan(s) | origin/main | Tests |
|---|---|---|---|
| 20:xx | F (#205) | 86ac780 (FF) | 1250 |
| 20:xx | E (#73) | (no-op, already 2adc84b) | — |
| 21:xx | **A+C+D combined** (#185,#202,#192,#181) | **83962df** | **1305** (integrated) |
| 22:xx | **H+I combined** (#209 revise-return, #210 serving-commit) | **097031d** | **1313** + smoke |
| 22:xx | **G Parts 1-2** (#208 options/recommendation + no-brainer carrier) | **326083d** | **1326** (clean merge) |

### ALL MATHCITY PLANS LANDED (A C D E F G H I). Remaining: B (gascity deploy, gated+city-up); G Part 3 (body composer, held for Taylor's design edit); render/read side of options (#76 Field 8, separate).
### UNLATCH PREDICTION CONFIRMED (city scope): mol-dog-stale-db fired 22:00:16, first since 08-20, minutes after its root closed — #204 mechanism proven. Rig-scoped (fast-drain) still under QUIMBY's batched-sweep watch. Note: control-dispatchers observed draining the 44 blockers on their own (gt-qb3i4o self-closed 21:56) — the blocker sweep may be unnecessary.

## UNLATCH (#204 / mc-6px0) — DONE 2026-08-23 ~21:5x
- Taylor approved (direct in my session) + QUIMBY reconcile (57 not 52; QUIMBY's 52 was a truncated `--limit 500` census). Taylor confirmed --force directly.
- **57/57 stale order-run wisp roots CLOSED** (17 plain + 40 --force over wedged finalize). Final open order-run non-wisp = 0.
- Blockers LEFT OPEN, 44 captured (/tmp/unlatch-blockers.txt) — they carry no order-run: label so can't re-latch (QUIMBY store_reads.go:483).
- Prediction test (brief-shuffle-fast-drain firing) NOT yet observed at close time — QUIMBY watcher live from seq 6289959.

- Union merges resolved keep-both each time: diagnostics.toml + registry CODE_PATTERN now carry MGHW_ (A), MEVT_ (C), MMAY_ (F) together; D added no codes.
- **Plan B** (gascity #99): CODE DONE + FULLY VERIFIED, commit c608add0a on branch plan-b-pool-pressure (fork, NOT pushed). 6 files +178/−18, package cmd/gc. Go test TestPoolDesiredReadyBacklogExertsBoundedPressure RED→GREEN; 213 touched-family Go tests pass; go build/vet clean. Full `go test ./cmd/gc/` exit 1 = ONLY 3 PRE-EXISTING failures (bundled pack-order asset drift: gate-sweep/digest-generate missing in this worktree's embedded assets) — confirmed identical on base fd3508049, NOT #99 regressions. **Landing = gascity-fork gated rebuild+deploy, bundling #29 cherry-pick a48bce497 — waits on city-up + Taylor's restart gate.** P5.4 finding: ~2403 premise partly stale; subagent correctly expanded scope to build_desired_state.go:866 (else dead code); cold-boot cmd_start.go:1040 left on nil (first tick supplies pressure). Worktree plan-b RETAINED. **⚠️ Foreign stash flag:** a pre-existing `stash@{0}: RECOVERED: stray order_dispatch.go latchSkipLogAt (clark #90 hold)` sits in the gascity stash stack — subagent restored order_dispatch.go to HEAD and PRESERVED the stash; it is NOT ours (clark #90's). Do not drop it.
- **Plan G** (#208): RUNNING, branch plan-g-options @ 83962df. Parts 1-2 (options/recommendation + no_brainer carrier) proceed; PART 3 (decisions.py body composer rebuild) HELD until Taylor's design-page edit; parts 1-2 structured as additive metadata so nothing unwinds.

## Anomalies (→ QUIMBY dogfood log)
- E: #73 closed by 2adc84b (Aug 20) — plan authored Aug 23 against stale "open" premise. Bug 1's HELD-for-ruling is moot (code already on main, impact measured null).
- C: nothing in-tree emits brief.submitted today (only a comment claims brief-prep does); adopted brief-record-decision.toml's `gc event emit` shape as the real spec. _handle_decisions_to_briefs also creates briefs live but does NOT ring brief.submitted (left per scope — possible follow-up bead).
- D: #181's 162.7s is the S48 measurement (SURFACE-STATUS), NOT in issue #181's body (which shows a 120s-killed run). Substantiated but mis-cited in the plan. `_apply_bd_create` is in beads.py, not commission.py as the plan said.
- A: #199 UNDERCOUNTS — beyond the six name-rosters there are count-based assertions in test_mcp_client_harness.py (tool count 33→…) and test_mcp_server.py (DECLARED_TOOLS length) — a 7th/8th roster invisible to a name-mirror pass, only the full suite catches them. Fold into the #199 note.
- B: plan's file-scope ("city_runtime.go only") missed build_desired_state.go:866 — the authoritative materialization site.
- F: no #203-style served-schema e2e test exists for mayor_boot (coverage gap).
