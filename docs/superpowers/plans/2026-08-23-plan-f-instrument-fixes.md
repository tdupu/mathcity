# Plan F — Small Instrument Fixes (#181, #205) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. Repo-side mctl work, fleet-independent, no design unknowns.
> NOTE the deconfliction: #181 was provisionally attached to Plan D's subagent as its feeder —
> whichever subagent (D or F) reaches it FIRST takes it and tells BART, who tells QUIMBY;
> the other treats it as done. #206 (priority mapping) is NOT here — it ships inside
> Plan A Task 2's shared mapper.

**Goal:** Two measured instrument defects fixed: `work_dispatch`'s subprocess budget is
smaller than `gc sling`'s real cost (#181 — dispatch times out before it dispatches), and
`mayor_boot` renders an empty handoff chain indistinguishable from a missing one (#205).

**Premises (measured; re-verify):** live sling measured 162.7s / exit 0 vs a 120s budget
(S48, settled slow-not-hung); resolution alone 56s. `mayor_boot(rig=mathcity)` 2026-08-23
19:41 returned `recent_handoffs: []` while gt-iw0dc3 existed. brad's standing warning applies
to #181's shape: raising a budget is legitimate ONLY because the cost is measured and bounded —
cite the 162.7s measurement in the commit, and do NOT touch the unrelated 45s claim window.

---

### Task 1: #181 — dispatch budget raised to measured cost + margin

**Files:** the subprocess timeout constant in `mctl_core/work.py` (locate the 120s bound near
the dispatch subprocess call); test alongside existing dispatch tests.

- [ ] **Step 1: Failing test** — the dispatch path's timeout constant is ≥ 200s (pin the
  VALUE with a named constant `DISPATCH_SLING_BUDGET_SECONDS`, asserted directly, so the next
  drift is loud), and a fake sling running 150s completes without timeout.
- [ ] **Step 2–4: RED → set 200s named constant with a comment citing the 162.7s measurement
  → GREEN.**
- [ ] **Step 5: Commit** — `fix(mctl): work_dispatch budget 120s→200s; sling measured at
  162.7s (#181)`.

### Task 2: #205 — mayor_boot handoff chain honesty

**Files:** `mctl_core/mayor.py` (the recent_handoffs query); `assets/mctl/diagnostics.toml`
(+`MMAY_HANDOFFS_NOT_FOUND`); test in `tests/mctl/`.

- [ ] **Step 1: Locate the query** — determine at source whether it reads the rig store or the
  hq store, and what label/title filter it applies. Record the answer in the commit message
  (it settles #205's two root-cause candidates).
- [ ] **Step 2: Failing tests** — (a) with a handoff-shaped bead in the store the query should
  reach, `recent_handoffs` is non-empty; (b) with zero matches and a READABLE store, the
  response carries `MMAY_HANDOFFS_NOT_FOUND` (WARN) naming store + query — an empty list with
  no diagnostic is the failure being pinned (P6.2).
- [ ] **Step 3–4: RED → point the query at the hq store / fix the filter + add the diagnostic
  → GREEN + served-schema test.**
- [ ] **Step 5: Commit** — `fix(mctl): mayor_boot finds the handoff chain and says so when it
  cannot (#205)`.

### Acceptance

- A fresh session's `mayor_boot` lists gt-iw0dc3 (and successors); `work_dispatch` live sling
  completes within budget (verifiable only with the fleet up — record in §5 when it is).
- Both land behind Taylor's gate; rosters/diagnostics registry updated per #199 where touched.
