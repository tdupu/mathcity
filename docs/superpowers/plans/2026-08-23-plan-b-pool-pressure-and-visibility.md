# Plan B — Pool Pressure (#99) then Pool Visibility (#197) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. Phase 1 is gascity-core work in the fork (BART's rebuild lane);
> Phase 2 is mctl work. **Phase order is a hard constraint:** visibility tools shipped before
> the pressure fix would report a pool that nothing can grow — #153's "backend-only completion
> counted as progress," again.

**Goal:** Make ready-work backlog exert upward pressure on `poolDesired` (#99), then give the
typed surface the four pool tools (`get_pools`, `get_worker_pool_size`, `get_sessions`,
`adjust_worker_pool`) scoped in #197 — so "the run-operator pool is EMPTY and nothing grows it"
can neither happen silently nor be diagnosed only by shelling into tmux.

**Architecture:** Phase 1 patches the desired-count computation in gascity
(`cmd/gc/city_runtime.go:2403` — `poolDesired := result.PoolDesiredCounts`, which today keys on
in-flight work plus a static floor) to add a bounded ready-backlog term. Phase 2 adds mctl READ
tools projecting pool/session state from the same sources the supervisor uses, plus ONE gated
mutation (`adjust_worker_pool`) that follows the EffectPlan dry-run pattern.

**Tech Stack:** Go (gascity fork, rebuilt + redeployed via the update procedure), Python (mctl),
pytest + the #203 served-schema pattern.

**Premises (measured; re-verify):** S48–S50: mathcity `gc.run-operator` pool EMPTY while
work_ready > 0; Taylor's framing "a pool always exists — it can just be empty" (#99); the
commission adapter's step 5 refuses on exactly this (§4 row). 3,301 ready beads exerted zero
pressure (issue #99 body).

---

### Phase 1 — #99: ready-backlog pressure (gascity fork)

**Files:**
- Modify: `cmd/gc/city_runtime.go` (the `poolDesired` computation at ~2403)
- Test: colocated Go test alongside the existing desired-count tests (follow the file's
  existing `_test.go` sibling)

- [ ] **Step 1: Failing Go test** — a pool with `floor=1`, `cap=4`, 0 in-flight, and N≥3 ready
  beads routable to it must get `desired ≥ 2`; with 0 ready it stays at floor; desired never
  exceeds cap. Encode the falsifiable target from the issue: backlog↑ ⇒ desired↑ within bounds.
- [ ] **Step 2: RED** (`go test ./cmd/gc/ -run TestPoolDesired -v`).
- [ ] **Step 3: Implement minimal** — add a `readyBacklogTerm(pool) = min(cap-floor,
  ceil(readyCount / beadsPerWorker))` contribution; `beadsPerWorker` starts as a constant (3)
  read from the same config block as the floor, no new config surface (YAGNI).
- [ ] **Step 4: GREEN + full `go test ./...` for the touched packages.**
- [ ] **Step 5: Commit on a fork branch; hand to BART** — rebuild + redeploy follows the
  gascity update procedure and Taylor's gate. NOTE: this rebuild is the natural vehicle to
  carry the #29 cherry-pick (`a48bce497`) in the same deploy window — one restart, two fixes.
- [ ] **Step 6: Live acceptance (city up):** with the pile/ready backlog present, observe
  the run-operator pool grow above floor within one reconcile tick; record in the dogfood log.

### Phase 2 — #197: the four tools (mctl)

**Files:**
- Create: `assets/scripts/mctl_core/pools.py`
- Modify: `mcp_server.py` (+ six rosters, #199), `assets/mctl/diagnostics.toml` (`MPOOL_*`)
- Test: `tests/mctl/test_pools.py`

- [ ] **Step 1: `get_pools` / `get_worker_pool_size`** — read-only projection: pool name, floor,
  cap, desired, actual-awake, ready-backlog. Failing test first: a fixture city with one pool
  returns all six numbers; an unreadable source yields `unknown` per field with a diagnostic —
  NEVER zero (P6.2; `gates_status` is the house style to copy).
- [ ] **Step 2: `get_sessions`** — projection of live sessions with pool membership and
  REGISTRATION-vs-STAFFING made explicit: separate `registered` and `staffed` fields, because
  `gc agent list`'s conflation of the two was S49's "most convincing wrong signal."
- [ ] **Step 3: `adjust_worker_pool`** — EffectPlan mutation, dry-run default, bounded by
  [floor, cap], refuses (`MPOOL_ADJUST_OUT_OF_BOUNDS`) outside them; records an mctl trace.
  This is the LAST tool built, after the reads are trusted.
- [ ] **Step 4: served-schema tests for all four; rosters ×6; commit per tool.**

### Acceptance (whole plan)

- The §4 commission-adapter blocker ("step 5 refuses: pool EMPTY") is gone: pool grows under
  backlog, and the growth is visible from the typed surface.
- SURFACE-STATUS: §4 pool rows promoted to §2 with real verdicts; #99 and #197 closeable with
  live evidence, not green suites.
