---
name: using-mathpowers
description: Use when proving, refuting, researching, checking, or developing mathematical claims; when asking what is known, finding something to prove, attacking a skeleton, questioning an argument, or gathering background. Also accepts using-math.
---

<SUBAGENT-STOP>
Assigned a bounded leaf task? Follow that brief and its evidence gates; do not restart the top-level workflow.
</SUBAGENT-STOP>

**First invoke `using-superpowers`, then `math-workflow` in math mode.** Reuse an active workflow; process precedes dispatch, including quick status answers. Announce the route. If this is not mathematical work, return to the appropriate domain skill.

The coordinator carries the request through planning, execution, validation, and cleanup. Math mode produces proof/research artifacts; requested `.tex` work delegates to `using-latexpowers` within the same plan.

## Dispatch

| Situation | Route |
|---|---|
| “Is X proved?” | Reconcile live source and ledger per `math-workflow`; report evidence and review status. Missing row means unrecorded, not false. |
| “What is known/open?” / deep research | `math-workflow` research phase |
| “Are we reinventing the wheel?” / before new construction | `check-zero` |
| “What could we prove?” | `find-proposition`; consume its candidates and continue if proving is requested |
| “Prove X” / “refute X” | Pack `subdomains/proof-assist/PROVERS.md`; return evidence to the coordinator for review |
| “Attack the skeleton” / gaps in a prototype | `fill-in-prototype`; continue selected obligations within the plan |
| “I doubt that” / “are you sure?” | `doubt`; skepticism outranks a bare status answer |
| Conflicting claims / before harvest or promotion | `contradiction-check`; resolve the conflict before dependent work |
| “Gather background” / expository spec | `create-exposition` |
| Proof technique or analogy | `find-the-technique`; source leads return through verification |
| arXiv / scholarly papers / Stacks / Mathlib / mathematical data | `search-arxiv` / `search-scholar` / `search-stacks` / `search-mathlib` / `search-lmfdb` |
| A load-bearing citation or suspect source | `track-down-reference` |
| “Write it up” / any `.tex` output | `using-latexpowers` with the existing plan and evidence; no second intake |
| Formalization requested | State that this prose-research workflow does not supply formalization; identify an installed formalization workflow before promising execution |

User instructions and repository contracts take precedence over skills. Mathematical and LaTeX policy floors still apply. Missing dependencies or unresolved gates are reported explicitly; neither a plan nor a dispatched agent counts as task completion.
