# Plan C — mctl Event Participation (#202) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. **HARD GATE: do not start until the #204 latch remediation has
> landed and one rig-scoped order has been observed re-firing.** S50 ran #202's two refuters:
> an emitted event into a latched order layer changes nothing, and the condition-triggered
> drain (`brief-shuffle-fast-drain`) needs no event at all. This plan is about LATENCY and the
> adjudication doorbell, not about making the pipeline work — the latch fix does that.

**Goal:** mctl rings the city's doorbells: emit `brief.submitted` when a brief is deposited
through the typed surface (consumed by `brief-shuffle-on-submit`, trigger=event — registered
and verified S50) and `brief.decided` when a verdict is recorded (consumed by
`brief-decision-dispatch` + `post-decision-file-or-sendback`, both trigger=event on
`brief.decided`) — so typed deposits and typed adjudications start the pipeline within seconds
instead of waiting for a condition tick, and the adjudication path stops being silent.

**Architecture:** One new module `mctl_core/gc_events.py` with a single `emit(event, subject,
payload)` that shells to the gc event-emit surface (the same mechanism brief-prep's
submit-to-pile step uses — locate its exact invocation in `formulas/brief-prep.toml` and copy
it; do NOT invent a second emission path). Wire two call sites: `briefs_create`'s apply path
(after the pile markdown lands) and `briefs_adjudicate`'s apply path (after the verdict write).
Emission is best-effort by design (events are lossy; the condition backstop remains) — an
emit failure is a WARN advisory on the effect plan, never a FATAL.

**Tech Stack:** Python (mctl_core), the gc event bus (`.gc/events.jsonl` is the observation
instrument), pytest.

**Premises (S50-measured; re-verify at execution):** zero `brief.submitted` events have ever
been emitted by anything except the skill path; `brief-shuffle-on-submit.toml` and
`brief-decision-dispatch.toml` both exist, scope/pool verified; the mc-f045 adjudication
(2026-08-23) rang nothing — the live demonstration of the missing `brief.decided` doorbell.

---

### Task 1: the emitter

- [ ] **Step 1: Locate the skill path's emission** — read `formulas/brief-prep.toml`'s
  submit-to-pile step and record the exact command it uses to emit `brief.submitted`. The
  emitter must produce an event indistinguishable in shape (type, subject, payload keys) from
  the skill path's, so consumers cannot tell the producer apart. Paste the found command into
  this plan before coding (it is the spec).
- [ ] **Step 2: Failing test** — `emit()` invokes that command with the composed subject/payload
  (recording fake); on subprocess failure returns an advisory diagnostic
  (`MEVT_EMIT_FAILED`, WARN) and does not raise.
- [ ] **Step 3–5: RED → implement → GREEN → commit.**

### Task 2: wire `briefs_create` (brief.submitted)

- [ ] **Step 1: Failing test** — a live (`dry_run=false`) `briefs_create` apply calls `emit`
  exactly once with `brief.submitted` and the brief id as subject; a dry_run calls it zero
  times (#188's mkdir-on-dry-run is the cautionary precedent: preview must have NO side
  effects, including events).
- [ ] **Step 2–4: RED → wire → GREEN + served-schema test still passing → commit.**

### Task 3: wire `briefs_adjudicate` (brief.decided)

- [ ] Same shape as Task 2. Payload must carry the verdict and (post-#152) `adjudicated_by`,
  because `brief-decision-dispatch` branches on approve/reject/revise/defer.

### Task 4: live acceptance in the running city

- [ ] Deposit a synthetic brief through the typed surface on a scratch-safe rig; within one
  tick observe in `.gc/events.jsonl`: `brief.submitted` → `order.fired
  brief-shuffle-on-submit:rig:<rig>`. Adjudicate it; observe `brief.decided` →
  `brief-decision-dispatch` firing. Record both seq numbers in the dogfood log.
  **If the order layer does not consume the events, STOP and re-open the routing question
  rather than patching around it** — that outcome would refute this plan's premise and the
  finding outranks the feature.

### Acceptance

- Typed deposit → gates within seconds (not the next condition tick); typed adjudication →
  dispatch order fires. #202 closes on the LIVE observation, not the green suite.
