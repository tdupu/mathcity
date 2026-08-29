# Adjudication write-path + mathcity dispatcher gap — design

| Field | Value |
| --- | --- |
| Status | Draft — awaiting owner approval |
| Date | 2026-08-27 |
| Author | clark (outside agent) |
| Supersedes | the ad-hoc three-item plan rejected by `check-plan-hygiene` (verdict: revise, 10 P-rule violations) |

## Why this exists

An earlier version of this plan was verdicted **revise** against
`subdomains/dev/POLICY.md`. This document re-derives it around the
constraints rather than patching it. Each work item below names the rules
it discharges.

## §A — Agent context (P3.5)

Executes as an **outside agent** (Claude Code session, not `GC_AGENT`).
Conservative git policy: no commit, no push, no rebase. `~/repos/*` is
read-only to this session (LP1, `parallel-repos-policy`); content destined
for a `~/repos` checkout is handed to BART, who takes it through the
`authorize-git-operation` gate. No step here mutates the live city without
an explicit owner decision recorded in §F.

## §B — What was measured (all [measured] unless tagged)

1. `mathcity/core.control-dispatcher` is configured and `active` in
   `gc agent list`, and has **zero sessions**. 14 control-dispatcher
   sessions exist across 13 rigs plus one city-level; mathcity is the only
   rig configured-active with none. Its one unblocked frontier step
   (`mc-0njx`) is routed there, so nothing can claim it.
2. The `mathcity/gc.run-operator` queue is latch-poisoned. Of the oldest 20
   unassigned beads routed to it, **15 carry `gc.kind=workflow`** — latch
   roots a pool worker must refuse. `mc-upgv` is #2 by age; `mc-5hu`
   (2026-08-20) is #1. Livelock, not deadlock.
3. The two causes are **independent and both required**. Starting the
   dispatcher does not unpoison the queue; unpoisoning the queue does not
   give the frontier step a worker. Any proposal addressing one alone is a
   partial fix.
4. `mctl briefs adjudicate` exposes no `--adjudicated-by`
   (`--verdict/--reason/--option/--dry-run/--city/--rig/--json`), and its
   own dry-run raises `MBRF_ADJUDICATOR_UNRECORDED`. The MCP tool
   `briefs_relay_adjudication` **does** take `adjudicated_by` and routes
   through the same mctl core. Filed as `mc-ewapk`.
5. The skill's claim that `gt-*` beads have no `mctl` route is **stale**.
   The rig is registered as `hq` (root `<home>/gt`); `--rig hq`
   resolved on 8 of 8 live calls. The skill names the wrong string, not a
   missing route.
6. The live city imports `<home>/repos/mathcity` (`city.toml`
   `[defaults.rig.imports.mathcity] source`). `~/gt/mathcity` is a distinct
   checkout, currently byte-identical for the affected skill but **not**
   what the city loads.
7. `~/.claude/skills/adjudicate-brief` is a symlink into a materialized
   sink. Editing it is a flat P1.3 fail.

## §C — Refuted; do not re-propose

- *"An unreleasable claim froze the convoy."* The claim was released twice
  over — one worker ran `bd unclaim`, another let the lease expire. The
  `gc.session_id` stamp on `mc-upgv` names a session absent from all live
  rows. Orphan residue, not a lock.
- *"`mc-upgv` is unassigned, so routing never happened."* There is no
  `assignee` key on task beads; the key is `owner` and gascity does not use
  it for dispatch. Routing is `gc.routed_to` metadata, and `mc-upgv` **is**
  routed, as are 26 of its 36 step beads.
- *"83 roots / 38 open / 28 claimable is one rig's exposure."* Wrong in both
  directions. Live exposure is **30 claimable latches on 2 queues**, both
  mathcity-owned. hecke (206) and gascity-packs (257) latch roots carry an
  empty `gc.routed_to` — inert and unroutable, a separate quieter problem.
- *"`gc.run_target` is retired."* Retired as a **runtime wire field** only;
  still honoured at compile time as a formula input.

## §D — Work items

### W1 — Root-cause the missing dispatcher (investigate; no mutation)

The prior plan said "start the session." That is a hand-start, which fails
the P1.1 replay litmus and is a P1.17 hack: it names no cause and states no
invariant preventing recurrence.

Deliverable: the reason mathcity alone lacks a session, and a fix that flows
through pack config (P1.2) — **or**, if a hand-start is genuinely needed
first, it is labelled *workaround*, carries the root-cause bead, and says so
(P1.17 named-workaround path). First place to look: `[[named_session]]`
entries silently unroutable (cf. `build-basic-fleet-dead-config`).

Read-only until §F.1 is answered.

### W2 — Correct `adjudicate-brief` (two defects)

Edit the **pack source**, never the sink (P1.3, P2.1). Canonical path is
`~/repos/mathcity/skills/adjudicate-brief/SKILL.md`, which is BART's lane —
so this is a content handoff, not an edit by this session (§F.2).

1. Replace the `gt-*`/`MCTL_CONTEXT_UNKNOWN_RIG` paragraph: the rig is `hq`.
   Keep a stop-and-report path for genuinely unmapped prefixes.
2. Change the prescribed write to the attributed one (see §E).

Runs `improve-documentation` before completion (P3.6).

### W3 — Land the two-cause evidence for `mc-67snh`

`mc-67snh` is adjudicated. Rewriting its content is a P1.19 violation.
Instead: create a **new brief through `mctl`** (P7.1 — `mctl` owns every
brief artifact; no hand-authored `.md`), linked to `mc-67snh`, carrying §B
and §C. §1 states the question only; measured findings go in §6
(`brief-evidence-belongs-in-s6-not-s1`). It must carry a recommendation —
that is what the original was sent back for.

### W4 — Re-cast `gsp-tqaeqb`

Its recommendation content exists but binds to no §2 heading; more
importantly it is written as a decision already taken by the agent that
wrote it, then deposited as `pending`. Re-cast as an actual choice, through
`mctl` (P7.1), same append-don't-rewrite constraint as W3.

## §E — Wheel-check (P1.20)

Surveyed alternatives for the attribution defect in W2:

| # | Alternative | Verdict |
| --- | --- | --- |
| 1 | Add `--adjudicated-by` to the `mctl` CLI | **Rule out for this plan.** It is the right long-term fix and is filed as `mc-ewapk`, but the skill does not need to wait on it. |
| 2 | Point the skill at the existing `briefs_relay_adjudication` MCP tool | **Adopt.** The capability already exists in core and was measured working today — 8 verdicts attributed through it. P7.4 prefers extending an adjacent surface over building one; P7.2 makes MCP a sibling consumer, not a chain. |
| 3 | Wrapper script that patches attribution after the canonical write | **Rule out.** A second writer (P7.1) and open bash (P7.4) — the exact defect P7.1 was written about. |

Gap filed, not routed around (P7.3): `mc-ewapk`.

## §F — Impact (P4.1 / P4.2)

**Upstream.** Nothing here touches gascity core or any pack outside the
owned set. No GitHub issue or PR is filed, so P3.1/P3.2 are not engaged.
`mc-ewapk` targets `mctl`, which is owned.

**Downstream.** W2 changes the call path the skill prescribes for every
adjudication consumer (dashboard, MCP, clerk, terminal). It introduces no
new contract — the MCP path already works and is already what produces
attributed verdicts; the change makes the skill match observed behaviour.
W1, if it results in a config change, alters city-wide session startup and
must go through pack imports rather than a hand-edit (P1.2).

**Aggregate (P4.3).** W3 and W4 both write brief artifacts in the same rigs;
serialize them, since `mctl` does not scope `artifact_root` per bead
(`gsp-1bmxuz`).

## §G — Open decisions (owner)

1. **W1 execution.** Investigate-only, or authorize a labelled workaround
   hand-start once the cause is named?
2. **Checkout of record for mathcity pack edits.** The city imports
   `~/repos/mathcity`; `~/gt/mathcity` is read-write for this session but
   not loaded. Confirm the handoff-to-BART route for W2.
