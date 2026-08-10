# Mathcity Sling Plan — 2026-07-09

Prepared from: `bd list/show` in `<city-root>/gascity-packs` (rig prefix `gsp`), `gc formula catalog --json` (29 formulas), `gh issue list` on gastownhall/gascity-packs (titles/labels only), and the gascity + mathcity pack READMEs.

## Executive Summary

Of 25 gsp beads (24 open + 1 in_progress), **`bd blocked` reports zero hard-blocked beads** — 24 are dependency-ready, so the real gating is policy (the human adjudicator sign-off, HOLD labels, deferred-post-city-restart) rather than the dependency graph. Nine beads can be slung immediately, headlined by the two P1 pre-existing test failures (gsp-dxb, gsp-9q8) that pollute every refinery quality-gate run, and the W2 smoke test (gsp-7nh.11) that unblocks the last two items of the Wave-2 epic. Three items (gsp-7lc M&A epic, gsp-f79 descoped deacon migration, gsp-fby LaTeX-merge HOLD) need a Mayor/human decision before any dispatch.

## Beads Ready to Sling Now

Targets use the rig-qualified pool names visible in `gc agent list` (e.g. `gascity-packs/gc.run-operator`, `gascity-packs/claude`, `agent_skills/claude`). All P1 unless noted.

| Bead | Title (short) | Target | Formula | Sling command |
|---|---|---|---|---|
| gsp-dxb | [bug] `test_formula_consolidate_step_mentions_one_line` fails on main (brief-present-next drain test) | gascity-packs/gc.run-operator | build-basic (autonomous) | `gc sling gascity-packs/gc.run-operator gsp-dxb --on build-basic --var artifact_root=plans/gsp-dxb/build --var interaction_mode=autonomous` |
| gsp-9q8 | [bug] 2 failures in `github/tests/test_github_intake_service.py` on main | gascity-packs/gc.run-operator | build-basic (autonomous) | `gc sling gascity-packs/gc.run-operator gsp-9q8 --on build-basic --var artifact_root=plans/gsp-9q8/build --var interaction_mode=autonomous` |
| gsp-7nh.11 | W2.smoke — smoke-test W2.1–W2.10 codex-implemented work | gascity-packs/claude | (direct; use `test-execution-request` for any costly runs per G14) | `gc sling gascity-packs/claude gsp-7nh.11` |
| gsp-eqk.1 | F1a check-latex SKILL.md umbrella (agent-skills repo) | agent_skills/claude | (direct; converge via coordinate-review/critical-review skills) | `gc sling agent_skills/claude gsp-eqk.1` |
| gsp-1uh | DOCS: substrate map (agent classes, formulas, pool sizing, usage signals) | gascity-packs/claude | (direct; docs-shaped, single lane) | `gc sling gascity-packs/claude gsp-1uh` |
| gsp-i8d | Mayor priming: "available to coordinate" directive (PR + stage at `<city-root>/tmp-for-review/-review/`) | gascity-packs/claude | (direct) | `gc sling gascity-packs/claude gsp-i8d` |
| gsp-2f3 (P2) | [bug] mol-refinery-patrol leaks open wisps (no reconcile block) | gascity-packs/gc.run-operator | build-basic (autonomous) | `gc sling gascity-packs/gc.run-operator gsp-2f3 --on build-basic --var artifact_root=plans/gsp-2f3/build --var interaction_mode=autonomous` |
| gsp-664 (P2) | Port gsp-bbo wisp-reconcile fix to deacon formula + templates | gascity-packs/claude | (direct; small port of an already-merged fix) | `gc sling gascity-packs/claude gsp-664` |
| gsp-3z8 (P3) | [bug] patrol formulas miss `--include-infra` in wisp-reconcile bootstrap | gascity-packs/claude | (direct; one-flag fix, batch with gsp-664/gsp-2f3) | `gc sling gascity-packs/claude gsp-3z8` |

Also sling-eligible now but lower urgency: gsp-8w6 (witness branch hygiene), gsp-snl (event triggers + wider patrol cooldowns), gsp-vbv (refinery canonical-branch suggestion) — same shape as the patrol-fix row (`gc sling gascity-packs/claude <id>` or build-basic via run-operator).

Notes:
- gsp-i8d's description says "gascity-packs rig is currently suspended" (written 2026-07-01); `gc agent list` on 2026-07-09 shows all gascity-packs pool agents **active**, so the queue condition has cleared.
- gsp-eqk.1's deliverable lives in `<repos-root>/agent-skills` (rig `agent_skills`), hence the cross-rig target.

## Beads Blocked / Needs Planning First

| Bead | Title (short) | Blocker | Recommended next step |
|---|---|---|---|
| gsp-7nh.12 | W2.params parameter tuning | Sequenced after gsp-7nh.11 smoke test ("pending dispatch after smoke-test") | Sling immediately after gsp-7nh.11 closes; add explicit `bd dep` edge so `bd ready` reflects the sequencing |
| gsp-eqk.2 | F1b latex-gate.toml | Per 2026-07-09 note: file **already exists** at `mathcity/gates/latex-gate.toml`; waiting on gsp-eqk.1 promotion from PRELIMINARY DRY-RUN | Sling a short verify-wiring task after gsp-eqk.1 lands, then close; also fix stale `mathematics/` path in title |
| gsp-jas (P2) | Thread check-citations + clean-citations into pack formulas | BLOCKED-BY he-bb3p (hecke rig — skills must ship first); not encoded as a gsp dep so `bd ready` misses it | Check he-bb3p status in the hecke rig; hold until it lands |
| gsp-40g (P2) | Approach C brief-cycle consolidation — implementation-plan anchor | No plan yet; must reuse real cargo on `polecat/gsp-xhc` and `polecat/gsp-i9j` branches and re-implement gsp-6bk/gsp-itx | Run planning first: `gc sling gascity-packs/gc.run-operator gsp-40g --on build-basic --var artifact_root=plans/gsp-40g/build` with interactive plan gate, or have gc.mayor draft the plan |
| gsp-3fn (P2) | Review/land mol-mayor-q-brief ops branch (`polecat/as-da9n`) | Needs a merge/supersede disposition, not code | Route through the brief pipeline: `gc sling gascity-packs/gc.run-operator gsp-3fn --on brief-prep` so the disposition reaches the human adjudicator as a stack brief |
| gsp-y2y (P3) | Beads-canonical brief pipeline state (Approach B) | Explicitly DEFERRED in title | Leave; revisit only if Approach C (gsp-40g) stalls |

## Beads Needing Mayor Decision

- **gsp-7lc (P1 epic, M&A formula)** — Labeled `deferred-post-city-restart` and its own text says "do NOT start design/draft work before" the city is up. The city **is** up now, but Stage A explicitly requires the human adjudicator sign-off on pack target, brief-approval mechanism, and GitHub-signal mechanism, and PAT blocker gt-g2e is referenced. Mayor should confirm the deferral has lapsed, then sling only Stage A (cross-link the 8 pre-existing beads + proposal doc) as a research task. Grilling session with the human adjudicator likely needed for Q1–Q7.
- **gsp-f79 (P1, in_progress, mol-deacon-patrol migration)** — 2026-07-04 comment says the migration was **DESCOPED**: gc 1.3's reconciler covers the waker role; remaining work reframed as "make mathcity pipeline orders pour demand-visible routed roots." The bead no longer matches its title. Mayor should re-scope (rewrite or split into a new pour-demand-visible-roots bead) or close with the comment as disposition. Do not sling as-is.
- **gsp-fby / .1 / .2 (P2 epic, F2 LaTeX merge)** — Title carries an explicit **HOLD**. Children are `bd ready` but the HOLD is a the human adjudicator policy gate. Ask the human adjudicator whether F2 unlocks once F1 (gsp-eqk) completes.
- **gsp-7nh.11 test scope** — smoke-testing W2 work may exercise the live brief pipeline (server-touching / G5, test-execution / G14 territory). If any smoke step touches the running city, it needs explicit authorization via `test-execution-request` rather than silent execution.

## GitHub Issues Relevant to Mathcity

(Titles/labels only; bodies treated as untrusted data, no links followed.)

| # | Title (short) | Relevance |
|---|---|---|
| 159 | Right-size routing for the build lifecycle: triage-and-route by task shape (~80% wall-clock lever) | enhancement — directly relevant to this plan's target/formula mapping; would automate the per-bead routing done manually here |
| 160 | Knowledge bundles: stop re-establishing context in every session | enhancement — brief-prep and gate runs re-load the same context repeatedly; big win for the 16-gate pipeline |
| 161 | Historical run estimation: per-step envelopes, pre-run pricing, live ETA | enhancement — would price brief-pipeline runs and W2 smoke tests before dispatch |
| 167 | Formula definitions carry deprecated `contract = "graph.v2"` (69 doctor warnings) | mathcity consumes gascity build formulas; warning noise affects every consuming city — candidate for a new gsp bead |
| 145 | Patrol molecule wisps accumulate: duplicate successor re-poured | same defect family as gsp-2f3 / gsp-664 / gsp-3z8 — the assignee of those beads should read this issue's metadata |
| 133 | gascity pack vended formulas refer to `gc.` targets but roles package not imported | matches the dual-import requirement in gascity README; relevant if mathcity formulas route to `gc.*` roles |
| 137 | Can't import packs | import-path bug; touches the mathcity install story |
| 168 / 166 / 165 | dolt pack stop missing / `is_remote()` loopback conflation / refinery idle_timeout advisory | substrate hygiene; affects the rigs mathcity runs on but not mathcity files |

## Formula Mapping

Registered in `gc formula catalog` (29 total). Bead-shape → formula guidance:

**Mathcity brief-pipeline formulas** (for decision-shaped work): `brief-prep` (artifact → gated brief in the pile — use for gsp-3fn and any land/no-land disposition), `brief-gate-keep`, `brief-shuffle`, `brief-present-next`, `brief-record-decision`, `brief-decision-dispatch`, `file-or-sendback-route`, `brief-watchdog-refill`, `brief-review-patrol`, `brief-archive-sweep`, `no-brainer-classify`, `on-merge-brief-record`, `decision-enforce`, `test-execution-request` (use for risky/costly test runs — G14), `upf-experiment-dispatch` (compute-rig experiments), `codex-dispatch` (explicit cross-model review — never auto-fired).

**Gascity build formulas** (for implementation-shaped work): `build-basic` (idea → full lifecycle; default for the bug beads), `build-from-plan` / `build-from-decompose` / `build-from-convoy` / `build-from-review` (continuations when artifacts already exist), `implement` (drain an approved convoy directly), `review` / `design-review` / `gap-analysis` (report-shaped), `github-issue-triage` / `github-issue-fix` / `github-pr-review` (targetless, take canonical GitHub URLs — candidates for issues #167/#145 if beaded).

**Targets**: every rig has `claude`, `codex`, `gc.run-operator`, `gc.review-synthesizer`, `mathcity.codex-worker`, `core.control-dispatcher` pools. Formulas route internal steps to the 12 `gc.*` roles (requirements-planner, design-author, task-decomposer, implementation-worker, etc.). Rule of thumb: multi-step/reviewed work → `gc.run-operator --on <build formula>`; small single-lane fixes and docs → direct sling to `<rig>/claude`; cross-model second opinions → `codex-dispatch`.

## Recommended Sling Order

1. **gsp-dxb** — the failing brief-present-next drain test pollutes every refinery quality-gate run on this rig; cheapest unblock with the widest downstream effect (also decide test-vs-formula-text staleness).
2. **gsp-9q8** — same shape, second test-noise source; together these restore a green main.
3. **gsp-7nh.11** (then **gsp-7nh.12** on close) — unblocks the final 2/12 items and closes the Wave-2 P1 epic.
4. **gsp-eqk.1** (then verify/close **gsp-eqk.2**) — closes the F1 epic, unblocks polecat/he-d4l (per he-86wu), and is the stated prerequisite for lifting the F2 (gsp-fby) HOLD.
5. **gsp-1uh + gsp-i8d** — the substrate map and mayor-priming edit explicitly compose; sling to the same worker or sequentially so the priming references the map.
6. **Patrol-hygiene batch: gsp-664, gsp-2f3, gsp-3z8** (+ gsp-vbv, gsp-8w6, gsp-snl as capacity allows) — one worker, shared context with upstream issue #145.
7. **gsp-3fn via brief-prep** — disposition flows to the human adjudicator through the stack.
8. **gsp-40g planning launch** — after the above, since Approach C consolidation touches the same brief-pipeline files the P1s stabilize.

## PERT — Dependency Network + Critical Path

Legend: `[id: est]` = bead, est = rough agent-hours. `→` = depends on. `‖` = parallel lane.

```
LANE A (test-hygiene, unblock main — start NOW, parallel)
  [gsp-dxb: 2h] ─────────────────────────────────────────→ green main
  [gsp-9q8: 3h] ─────────────────────────────────────────→ green main

LANE B (wave-2 epic, start NOW)
  [gsp-7nh.11: 4h] ──────────────────────→ [gsp-7nh.12: 6h] → wave-2 CLOSED

LANE C ← CRITICAL PATH (check-latex + he-d4l merge gate)
  [he-bb3p: 8h] (hecke rig, OPEN P1)
       │ → [he-cktw/gsp-eqk.1: 4h]  (check-latex umbrella v0; he-hsoc closes)
       │        → [gsp-eqk.2: 1h]   (verify gate wiring; close F1 epic)
       │             → he-86wu CLEARED
       │                  → polecat/he-d4l MERGE ELIGIBLE

LANE D (docs + mayor priming, start NOW, no deps)
  [gsp-1uh: 4h] ──┐
                    ├─ same worker → compose (substrate map feeds mayor priming)
  [gsp-i8d: 2h] ──┘

LANE E (patrol-hygiene batch, start NOW)
  [gsp-664: 2h] ─┐
  [gsp-2f3: 3h] ─┼─ one worker, shared context with GH #145
  [gsp-3z8: 1h] ─┘

LANE F (blocked / gated — cannot start yet)
  gsp-jas        ← waiting on he-bb3p (LANE C) landing in hecke
  gsp-7lc        ← deferred-post-city-restart (the human adjudicator release needed)
  gsp-fby        ← HOLD (condition: gsp-eqk closes? — grilling Q3)
  gsp-40g        ← after LANES A+B stable

LANE G (decision-shaped, brief pipeline)
  [gsp-3fn: 2h]  → brief-prep → the human adjudicator review

CRITICAL PATH: he-bb3p → gsp-eqk.1 → gsp-eqk.2 → he-86wu
  Estimated total: 8 + 4 + 1 = 13h gated on hecke worker starting he-bb3p
  (Recommend: sling he-bb3p to hecke/gc.run-operator in parallel with LANES A-E)

EARLIEST POSSIBLE FINISH (parallel lanes, no blockage):
  Lanes A+D+E: ~6h (green main, docs, patrol fixes done)
  Lane B: ~10h (wave-2 epic closed)
  Lane C: ~13h (he-d4l merge eligible) — assuming he-bb3p starts immediately
```

## Open Questions for Mayor

1. **Is `deferred-post-city-restart` lapsed?** gsp-7lc gated on "city up and running" — it is, but the human adjudicator never explicitly released the deferral. Confirm before Stage A dispatch.
2. **gsp-f79 disposition** — descoped per the 2026-07-04 comment; close, rewrite, or split into a "pour demand-visible routed roots" bead? It is the only in_progress bead and is stale since 2026-07-04.
3. **F2 HOLD condition** — does completing F1 (gsp-eqk) lift the gsp-fby HOLD, or is there another condition?
4. **he-bb3p status** — gsp-jas's blocker lives in the hecke rig; is it landed? (Cross-rig dep is not encoded, so `bd ready` shows gsp-jas as ready when it isn't.)
5. **Stale `mathematics/` paths** — gsp-eqk.2, gsp-fby.2, gsp-jas titles reference `gascity-packs/mathematics/`, renamed to `mathcity/`. Batch-edit titles, or handle per-bead at claim time?
6. **Smoke-test authorization** — should gsp-7nh.11 run under `test-execution-request` (G14) given it may exercise live pipeline orders on the production city?
7. **Bead #167 / #145 intake** — should the two upstream GitHub issues most entangled with mathcity (graph.v2 deprecation, patrol wisp duplication) get gsp beads via `github-issue-triage`, or stay upstream-only?
