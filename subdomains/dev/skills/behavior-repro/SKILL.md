---
name: behavior-repro
description: >-
  Use as step 1 when a complaint about an agent's behavior has to become
  evidence, before any cause is diagnosed or any artifact edited. Not for code
  defects.
---

# Behavior repro

A complaint is not evidence. Evidence is three written statements plus a fresh
agent, holding nothing but those statements, doing the undesired thing.

## Write down three things

- **Undesired** — what the agent did, decidable from the agent's output alone.
  "Called the change tested while its own report names no test it ran" is
  checkable. "Never actually ran the tests" is not: that is a claim about
  actions. Restate such a complaint as its output signature, or report it
  **unsettlable**.
- **Desired** — what it should have done instead, stated so a reader of the
  output alone could tell the two apart.
- **Situation** — the task, the inputs, and what the agent was working from.
  The complainant knows things the fresh agent will not. Those things go here
  or the repro will not run.

## Then confirm it reproduces

Hand the situation to a fresh agent. Give it the task, never the complaint: a
prompt that names the undesired behavior invites it, and you will have tested
your own phrasing instead of the artifact.

Behavior is stochastic: one clean run is not an acquittal, one bad run is not
proof. Run it k times against the unedited artifact — default k=3, fixed here
for the rest of the run — grading each run against the written undesired/desired
pair and nothing else, and record the count. This count is the pre-edit floor,
taken here, before anything has been changed; the later paired comparison in
[[behavior-verify]] runs its own control arm, which must still clear this floor.

**The floor is a majority of k.** Below the floor, stop here: before a cause is
sought, before an edit is made.

## Terminal outcomes

- **confirmed** — at or above the floor; what [[behavior-cause]] consumes.
- **unreproducible** — never reproduced.
- **underpowered** — reproduced below the floor. Give the counts and stop short
  of ruling on the complaint: from inside these runs a rare-but-real behavior
  and a bad repro look alike.
- **unsettlable** — the situation cannot be described without naming the
  undesired behavior, or the only way to get the behavior is to ask for it.

No repro, no repair: only **confirmed** continues; the rest are not a licence to
edit prose and declare victory.
