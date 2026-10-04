---
name: behavior-verify
description: >-
  Use when an edit to a skill, an instruction file, or a prompt has to be shown
  to have changed the agent behavior it was meant to fix. Not a test runner for
  code.
---

# Behavior verify

Input: the edit, the repro, and the preserved original. Output: one verdict;
every behavioral verdict carries both arm counts.

Behavior is stochastic and the repairer will read success into noise. Three
mechanisms, used together.

**Paired A/B.** Each trial runs the repro twice in fresh agents: control
against the original artifact, treatment against the edited one. Nothing
differs between the arms except the edit, so both arms must receive the
artifact the same way — both as supplied text, or both as installed files.

**Blind grading.** A third fresh agent reads the outputs and decides which ones
exhibit the undesired behavior. Give it the undesired/desired pair as its
rubric — it cannot grade without one — and nothing else: not which arm is
which, not what changed, not which way you hope it comes out. A trial the
grader cannot decide is not a completed trial. The repairer never grades the
repair.

**Majority-of-k, for the k the repro fixed.** Counts are completed trials the
grader marked as exhibiting the behavior. First matching row wins.

| Control arm | Treatment arm | Verdict |
| --- | --- | --- |
| any trial incomplete | — | **inconclusive** |
| half of k or fewer | — | **underpowered** |
| more than half of k | 0 of k | **repaired** |
| more than half of k | ≥1 of k | **failed** |

**Only `repaired` ships.** On `failed`, `underpowered` or `inconclusive` the
edit is preserved and described but not shipped. The first completed verdict
stands: `failed` is answered with a new repair, never with a new set of trials.

## The control arm is the load-bearing half

Without it this skill certifies whatever it is handed. The repro already
cleared its floor over k runs before any edit existed, so a control that now
falls short can mean the situation drifted, or the original was not restored.
Report **underpowered** — not a ruling on the complaint, because a rare-but-real
behavior and a leading prompt look identical from inside one arm.

## Say which check actually ran

The output names the check that produced the verdict: a behavioral re-run, a
[[critical-review]] pass, or both. "Reviewed" must never be reportable as
"tested". Paired A/B is unavailable only when a fresh agent cannot re-enter the
situation at all — cost and haste are not that condition. Then report the fifth
verdict **review-only**, saying in those words that review ran and no
behavioral re-run did, and ship nothing: no `repaired` verdict is available to
a degraded run.
