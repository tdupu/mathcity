---
name: lean-frontier-dump
description: Dump the mathematical frontier around a STUCK Lean goal — the goal state, what Mathlib actually has nearby, what is genuinely missing, and candidate routes — into a dated ai/ package. Use when a formalization attempt has exhausted its bounded retries and the honest next output is a recorded obstruction rather than another tactic. Trigger phrases "lean-frontier-dump", "dump the frontier around this goal", "I cannot close this goal", "what is missing to prove this", "this obligation is stuck", "frontier dump for a Lean obstruction". Sibling of frontier-dump (research frontiers); this one is specialized to formalization obstructions and is the escalation target of lean-formalize-prove. NOT for a goal that simply needs a different tactic — that is lean-diagnose. NOT for deciding whether a statement is right — that is lean-fidelity.
---

# lean-frontier-dump

## When this is the right skill

`lean-formalize-prove` bounds its proof/diagnose loop. On exhaustion the honest
output is a **recorded obstruction**, not another tactic. This skill produces it —
but only for the third row, after `lean-diagnose` has classified the failure:

| Diagnosis | Remedy | Here? |
|---|---|---|
| Proof engineering — right statement, wrong tactic | retry via `lean-diagnose` | no |
| Statement problem — unprovable as stated, or vacuous | back to `lean-align-statement` | no |
| Mathematical obstruction — theory is missing | **this skill** | yes |

Running this on row 1 spends a frontier-model call on a goal a different tactic
closes. State which row you are acting on, and your evidence.

## Dependency pre-flight (P1.14)

Before anything else, confirm you can reach a Lean project that elaborates and a
frontier-tier model. If either is absent:

```
I'm sorry, I can't do that — <what is missing>.
Run /lean-doctor (or make a frontier-tier model reachable) to set it up.
(This skill needs a live goal state and a reasoning-strong model to characterize
what theory is missing around it.)
```

Do not proceed on a partial baseline. A frontier dump built from a goal state you
could not actually print is fiction.

## Procedure

1. **Capture the goal state verbatim.** Print the actual Lean goal at the point of
   failure — hypotheses, target, instance context. Do not paraphrase it. Read the
   build's exit code directly; never pipe into `head`/`tail`, which reports the
   pipe's status and turns a failure into rc=0.

2. **Record what was already tried**, from the bounded loop's attempt log: tactics,
   lemmas applied, why each failed. A dump that omits this invites the frontier
   model to re-propose what already failed.

3. **Search before you claim absence.** Take the `lean-search` route, and
   `search-mathlib` / `search-stacks` where relevant. Enumerate what exists NEAR the
   goal: adjacent lemmas, the general form of which this is a special case, the same
   result over a different base.
   Record the exact queries you ran, not your conclusions about the library.

4. **Name the gap precisely.** State the mathematical content that is missing, as a
   statement someone could prove. "This is hard" is not a gap; "Mathlib has this for
   fields of characteristic 0 but the theory must work over ℤ, and the
   characteristic-0 proof uses division at step N" is a gap.

5. **Delegate to a frontier-tier model.** Identify the strongest reasoning model
   reachable from the current harness — decided at run time, never hardcoded. Pass
   the goal state, the attempt log, the search record, and the gap statement.
   Require the negative-result obligation explicitly: the worker must report what it
   **refuted** — routes that do not work, and why — as first-class findings, not as
   caveats.

6. **Write the dump** to `ai/YYYY-MM-DD-lean-<slug>/`, never overwriting; append a
   numeric suffix if the target exists. Confine writes to that folder.

7. **Record it in all three places or none:** the dump, a named gap entry in the
   gap document, and an open bead. `lean-formalize-verify` reconciles those counts
   against the project's `sorry`s, and a partial record is what that gate catches.

## Required dump

`report.md`, self-contained:

- **Goal** — the verbatim Lean goal state and its file:line.
- **Classification** — why this is a mathematical obstruction and not the other two
  classes, with the evidence for that call.
- **Attempted** — what was tried and how each failed.
- **Searched** — each query run, verbatim, and what it returned.
- **Nearest existing results** — Mathlib names, and how each falls short.
- **The gap** — stated as a provable proposition.
- **Candidate routes** — each with its cost and its risk, including any that would
  require changing the source statement (flag those: a statement change re-enters
  `lean-align-statement` and must be re-reviewed).
- **Refuted** — routes ruled out, with the argument. First-class, not a footnote.
- **Base-ring check** — whether the obstruction is an artifact of a
  characteristic/base-ring assumption. This is a recurring cause and cheap to check.

## What this skill must never do

- **Never weaken the statement to dissolve the obstruction.** Adding a hypothesis
  that makes the goal provable changes the theorem. Propose it as a route, flagged;
  do not apply it.
- **Never leave a silent `sorry`.** An unrecorded hole behind a green build is the
  most misleading state a formalization can be in.
- **Never report absence you did not search for.** An empty result is evidence
  about your query, not about Mathlib. Write "I searched X, Y, Z and found
  nothing", never "Mathlib does not have this".
- **Never trigger a cold Mathlib build.** If one appears unavoidable, stop and file
  a blocker.
- **Never write upstream.** TauCetiRoadmap is read-only to agents; derive a local
  copy instead.
