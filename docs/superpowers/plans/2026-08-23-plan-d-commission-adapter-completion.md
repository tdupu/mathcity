# Plan D — Commission Adapter Completion (#179/#180) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. **GATES: Plan B Phase 1 (#99) deployed, and #181's dispatch
> budget fix landed.** This plan is mostly verification and wrapping — S48 proved 4 of the 5
> steps by hand (`gh#1 → mc-7d0 → mc-60j → readiness "ready"`); the remaining work is the one
> blocked step plus making the lap repeatable without a human driving each call.

**Goal:** The city's first repeatable issue→molecule lap: one typed entry point that takes a
GitHub issue and leaves a claimable, staffed molecule — the reusable version of the #180
hand-run, closing the loop that #204's unlatch + Plans A–C open.

**Architecture:** No new machinery until the hand-run passes end-to-end. First re-run the five
steps against the fixed substrate and let each fix prove itself; only then wrap the sequence as
`commission_from_issue` (a thin composition of the four existing tools — `create_issue_bead` →
`commission_brief`/`briefs_create` → human `briefs_adjudicate` → `work_dispatch`), with the
human adjudication step REQUIRED in the composition (R3 governs; the #152 `adjudicated_by`
field, live since 6dc1bf4, is what makes the authority auditable).

**Tech Stack:** Python (mctl_core), pytest, the live city as the acceptance instrument.

**Premises (re-verify at execution):** step 5 refused on pool-EMPTY (#99 — Plan B fixes);
`work_dispatch` live sling measured 162.7s vs 120s budget (#181); `commission_brief` retry
leaves orphan beads (#192 — mc-7po is the standing evidence, deliberately left in place);
`gc formula cook` has no `--dry-run`, so the held rehearsal stays held.

---

### Task 1: #192 — one error boundary per commission create

**Files:**
- Modify: `assets/scripts/mctl_core/commission.py` (`_apply_bd_create` — today runs `bd create`
  then a SEPARATE `bd link` per source under ONE error boundary, so a retry accumulates bricks)
- Test: `tests/mctl/test_commission_idempotent.py`

- [ ] **Step 1: Failing test** — a create whose link step fails leaves NO orphan decision bead
  (either rolls back or records the partial with `metadata.commission_incomplete=true` that a
  retry adopts instead of duplicating); a full retry after transient failure yields exactly one
  brief.
- [ ] **Step 2–5: RED → restructure the boundary → GREEN → commit.**

### Task 2: re-run the five-step hand-lap against the fixed substrate

No code. A fresh MCP-only session executes, recording every call + trace id in the dogfood log:

- [ ] 1. `create_issue_bead` on a real open issue (NOT gh#1 — it already has mc-7d0/mc-60j
  history; pick the lowest-numbered open leaf issue without prior commissions).
- [ ] 2. `commission_brief` → verify exactly one brief, correct rig derived from the tracker.
- [ ] 3. Human adjudication via `briefs_adjudicate` (Taylor or his standing delegation), and
  verify `adjudicated_by` is populated on the bead — the first live exercise of #152.
- [ ] 4. `work_dispatch(dry_run=false)` → `applied:true`, molecule minted, and the sling
  completes within the post-#181 budget.
- [ ] 5. The molecule is CLAIMED (non-empty staffing on the pool Plan B grew) and its first
  step executes. Each step that refuses: file the refusal, stop, do not route around (CT13.4).

### Task 3: wrap as `commission_from_issue` (only after Task 2 passes clean)

- [ ] **Step 1: Failing test** — the composed tool returns the per-stage trace ids and STOPS
  at the adjudication stage with the brief pending (it never supplies a verdict — #194's
  lesson is baked into the composition's contract test: assert `verdict is None` and
  `blockers == ["MWRK010"]` after stage 2).
- [ ] **Step 2–4: implement the thin composition → served-schema test → rosters ×6 → commit.**

### Acceptance

- One command takes an issue to a pending brief; a human verdict takes it to a claimed,
  executing molecule; the whole lap's evidence is in traces + the dogfood log. #179/#180
  close on the live lap. §4's adapter row (and this plan) retire into §2 verdicts.
