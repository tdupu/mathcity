---
name: adjust-behavior
description: >-
  Start here when an agent did something undesired and you suspect the
  instructions it read — a skill, a project instruction file, a prompt
  template — rather than the code it ran. Runs the repro, cause, repair and
  verify steps in order.
---

# Adjust behavior

A skill fails by making an agent do the wrong thing plausibly, so the loop
needs evidence the behavior happened and evidence it stopped.

Run in order. Each step can end the run.

1. **[[behavior-repro]]** — pin the undesired behavior, the desired behavior,
   and the situation that triggers it, and confirm it reproduces often enough to
   measure. **No repro, no repair.**
2. **[[behavior-cause]]** — find the artifacts that plausibly produced it and
   establish who owns each. Keep the candidate list; step 4 can send you back
   to it.
3. **Repair.** Ask the question below, then edit. Preserve an unedited copy of
   every artifact you touch: step 4's control arm needs the original text.
   - *Skill files:* use a skill-authoring skill if your environment provides
     one. A convergence loop like [[fp-finder-skill]] enforces that no file
     grows, but **do not run it between the edit and step 4**: it rewrites
     lines unrelated to the repro, which breaks the one property the A/B
     rests on — nothing differs between the arms except the edit. Run it
     before the original is preserved, or after the verdict. And diff its
     output against your repair before accepting it: a loop that finds no
     improvement returns its input, so writing the result back deletes the
     fix while reporting success.
   - *Every other artifact* — instruction file, prompt template, policy prose —
     has no convergence engine, so nothing enforces that bar mechanically and
     it is yours to meet by hand: the file ends no longer than it started, or
     the repair states why it had to grow.
   - Then [[critical-review]], handed the repro, the blast radius, and both
     versions of the text. The claim under review is *this edit fixes this
     repro and causes no adverse effect elsewhere* — not the file in isolation.
     A convergence loop's own reviews see the file alone and do not discharge
     this step.
4. **[[behavior-verify]]** — re-run the repro against the text you will
   actually ship. Convergence and review can delete the repair while reporting
   success, so verify whatever came out of step 3, not the edit you made before
   it. **Only `repaired` ships.** On `failed`, return to step 3 with the next
   candidate from step 2; when it is exhausted the run ends unrepaired and
   reports that.

## Step 3, before the edit: ask this

**Can this be fixed by giving the agent better context rather than by adding a
rule?** Default yes. A rule, branch, or table needs a reason recorded with the
repair, and that reason must say why context alone cannot produce the desired
behavior. "A rule is more reliable" is not that reason unless the repro showed
it. A skill that has grown a lookup table has started deciding what the agent
should decide.

## Step 3, before [[critical-review]]: state the blast radius

The artifact is read by agents who did not file this complaint. Say **which
file grew during this run** — a file created this run counts as growth equal to
its whole length, and if the cause was uneditable and some other file gained
rules instead, the bloat was relocated, not prevented. Say what else reads the
artifact, what behavior could change that nobody asked to change, and whether
the edit removes a deliberate refusal to supply a default — softening one of
those makes the complaint go away by deleting the thing that was working.

## Any step: escalate rather than guess

When the cause is ambiguous, when two artifacts both explain the behavior, or
when review contests the repair: **use a frontier model** for a recommendation
([[frontier-dump]] if your store provides the mechanism). Do not edit both
candidates to cover the ambiguity.

Escalating succeeds as an escalation, not as a run: bring the recommendation
back to the step that escalated and finish from there. A run that stops at the
escalation reports that it repaired and verified nothing.
