# The Path to Dogfooding the Entire Issue Tracker

**Goal:** reach a state where the mathcity GitHub issue tracker drains itself — every
open issue becomes a dispatchable hygienic brief, the city executes it, and the work
closes the issue, with a human deciding only what genuinely needs judgment.

**Owner's statement of intent, verbatim:**

> *"The plan is eventually to get to a point where QUIMBY can dispatch some work which
> will then turn every mathcity issue into more mathcity work... As soon as we can get
> this issue in and give those agents the ability to turn the github issues into
> hygienic briefs which can be dispatched to the city we will essentially defeat the
> issue tracker autonomously from that point."*

---

## The loop, stated once

```
GitHub issue
   |  (1) paired bead                      #180   <- the OPEN SOURCE BEAD
   v
hygienic brief, adjudicated                #179   <- the edge that does not exist
   |  (2) work_dispatch(bead_id)           F0     <- armed 2026-08-22, needs a restart
   v
MOLECULE                                          <- never yet observed
   |  (3) city executes; artifact + evidence
   v
merged commit -> issue closes                     <- conservation: no close without a merge
   |
   +--> new findings file new issues, paired on arrival
```

**Every arrow is a place the loop can lie.** The whole design problem is that a broken
arrow and an idle arrow look identical, which is the finding this repo has hit sixteen
times. Each phase below therefore ends in something *observable*, not something
*callable*.

---

## Phase 0 — The primitives must not brick what they touch

**Nothing downstream is worth building while creating work destroys it.**

| # | Blocker | Owner | Done when |
|---|---|---|---|
| `#147` | mathcity/agent_skills cannot accept briefs at all (`MBRF035`) | sally | mathcity can receive its own repair work |
| `#173` | approving a sourceless brief permanently bricks it | mutt | creating a sourceless brief is REFUSED, not minted |
| `#169`/`#168` | `briefs_create` does no structural validation, writes no index row | mutt | a created brief is valid and indexed |
| F0 | live dispatch disarmed | owner ✅ armed | a restarted MCP server has the var and dispatch applies |

**`#147` is the sharp one:** the rig that owns `mctl` cannot receive a brief, while
`CT4.5` requires a brief before dispatch. **mathcity cannot currently commission its
own repair.** Phase 0 is not sequenced behind anything; it is the reason the rest is
theoretical.

**Exit test:** create a brief through the MCP for a real bead, adjudicate it, and have
`work_status` return `readiness: "ready"`, `blockers: []`. **That has never succeeded
end to end.**

## Phase 1 — Every issue has a source bead

**`#180`.** 81 of 99 open issues are unpaired. The paired bead is not bookkeeping — it
**is** the open source bead the brief in Phase 2 must point at.

Three parts, and the third is the one people skip: **a detector that can fail.** If it
cannot enumerate the tracker it reports `unknown`, never zero — an empty result from a
failed `gh` call must not render as "fully paired" (P6.2).

**Machine-readable pairing, not a title convention.** A regex guessing at `#N` in prose
is how `#156`'s citation went wrong.

**Exit test:** the detector reports zero unpaired, and a newly filed issue arrives
paired with no human step.

## Phase 2 — The issue → brief edge

**`#179`, the keystone.** Today `mathcity-issue-briefed` runs the loop *backwards*: it
drafts an issue body from a bead and **never files the issue**. That is
`finding → issue`. The loop needs `issue → dispatchable work`.

**The hard half already exists.** `create-issue-briefed` routes through the brief
pipeline and carries the `brief-producer.v1` contract with `file-brief` as its terminal
step. A sibling adapter overrides `intake` to take an **issue number** instead of a
source bead. Override by id; **do not append** — an appended step lands after
`file-brief` and breaks F8.1.

**`#177` supplies the typed tools** this edge calls: `decisions-to-briefs` and
`present-briefs`, both in the MCP, both producing output that *can be acted on*.

**Exit test:** one named issue in, one brief out, and `work_status` on that brief
returns `ready` with no blockers.

## Phase 3 — The first molecule

**One issue, end to end, fully instrumented.** Not a batch.

```
issue -> bead -> brief -> adjudicate -> work_dispatch(armed) -> MOLECULE -> steps -> artifact
```

**A dispatch that reports success and produces no molecule is the failure this whole
exercise was built to catch.** If it happens, the run has succeeded at its purpose.

**Exit test:** a molecule id exists, its steps advance, and an artifact lands. **This
has never been observed. Everything before Phase 3 is preparation for one measurement.**

## Phase 4 — Scale, with the brakes designed in first

Only after Phase 3. Three brakes, and they are not optional:

- **No infinite loops.** Standing policy: dispatchers must have explicit termination
  criteria. A tracker-draining loop is a dispatcher, and *"there are still open
  issues"* is not a termination criterion.
- **A WIP limit, not a queue depth.** Dispatch what the fleet can execute, measured by
  free slots, not by how many issues exist. Pull, not push.
- **Two failures park it.** An issue that fails twice is escalated, never retried a
  third time automatically.

**Blast radius stays on the ladder.** `low` acts, `medium` previews, `high` needs a
typed target name, **`gated` still goes to the human approval gate** — branch delete,
worktree removal, push, merge, bead delete. **Autonomy over the tracker is not
autonomy over the repository.**

## Phase 5 — What a human still decides, permanently

**This loop is not meant to reach zero human input, and saying so is part of the
design.**

- **Commissioning.** The authorization boundary is commissioning, not adjudication
  (owner ruling). An agent may relay a verdict; the decision to *want the work* is the
  owner's.
- **Anything `gated`.** Unchanged, forever.
- **Moot vs. real.** Closing an issue as moot is a judgment. Some of the 99 are moot;
  a loop that auto-closes them is a loop that hides its own mistakes.
- **New findings.** The city will produce more issues than it closes for a while.
  **That is the system working**, and the count going *up* during Phases 0–3 is
  expected, not regression.

---

## How this fails, and how we would know

| Failure | What it looks like | Guard |
|---|---|---|
| Dispatch reports success, no molecule | applied `true`, nothing runs | `CT13.4` — a refusal is named; report molecule id or NO MOLECULE explicitly |
| Brief created but undispatchable | brief exists, `work_status` blocked | the PAIR requirement, as acceptance not design note |
| Loop runs on stale code | fixes land, behaviour unchanged | `#164`/`#165`; restart servers after every merge, and verify by age |
| Issues closed without work | tracker drops, nothing shipped | conservation: no close without a merged commit cited |
| Runaway dispatch | fleet saturated, duplicate work | WIP limit; two-failure park |
| The detector cannot see | "zero unpaired" from a failed call | `unknown`, never zero |

**The pattern behind all six is one thing:** *a component that cannot answer is
indistinguishable from a component answering "nothing".* Sixteen instances this week.
Every phase gate above is written to make that distinction observable.

---

## Where we actually are

```
Phase 0   IN PROGRESS   #147 urgent, #173 owned, F0 armed but unverified
Phase 1   FILED         #180, 81 of 99 unpaired
Phase 2   FILED         #179 keystone, #177 tools
Phase 3   BLOCKED       zero molecules observed, all session
Phase 4   NOT STARTED   by design
Phase 5   STANDING      the human decisions, stated so they are not eroded by drift
```

**The honest summary: we have built a great deal of the machinery and have never once
watched a molecule run.** Phase 3 is one measurement, and everything before it exists
to make that measurement trustworthy.
