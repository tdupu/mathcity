---
name: using-mathpowers
description: Use when proving, refuting, researching or checking mathematical claims, gathering selected research files, or developing a coherent presentation from frontier dumps. Also accepts using-math and using-mathskills.
---

<SUBAGENT-STOP>
Assigned a bounded leaf task? Follow that brief and its evidence gates; do not restart the top-level workflow.
</SUBAGENT-STOP>

**First invoke `using-superpowers`, then `math-workflow` in math mode.** Reuse an active workflow; process precedes dispatch, including quick status answers. Announce the route. If this is not mathematical work, return to the appropriate domain skill.

The coordinator carries the request through planning, execution, validation, and cleanup. Math mode produces proof/research artifacts; requested `.tex` work delegates to `using-latexpowers` within the same plan.

## Dispatch

| Situation | Route |
|---|---|
| Frontier dumps / research files → context, outline or cohesive narrative | `math-workflow`'s [synthesis sequence](../../../../skills/math-workflow/references/synthesis.md); selected-file context via `create-exposition`, outline via `rapid-prototype`, filling via `fill-in-prototype` |
| One exact result with prerequisites to backfill | Fix the full target in the synthesis plan, then close its dependencies; final definitions still precede their use |
| “Is X proved?” | Reconcile live source and ledger per `math-workflow`; report evidence and review status. Missing row means unrecorded, not false. |
| “What is known/open?” / deep research | `math-workflow` research phase |
| “Are we reinventing the wheel?” / before new construction | `check-zero` |
| “What could we prove?” | `find-proposition`; consume its candidates and continue if proving is requested |
| “Prove X” / “refute X” | Pack `subdomains/lean/PROVERS.md`; return evidence to the coordinator for review |
| “Fill the prototype” / “attack the skeleton” | `fill-in-prototype`; fill established material, investigate selected gaps, review and return to the authorized synthesis stage |
| “I doubt that” / “are you sure?” | `doubt`; skepticism outranks a bare status answer |
| Conflicting claims / before harvest or promotion | `contradiction-check`; resolve the conflict before dependent work |
| “Gather background” / expository spec | `create-exposition` |
| Proof technique or analogy | `find-the-technique`; source leads return through verification |
| arXiv / scholarly papers / Stacks / Mathlib / mathematical data | `search-arxiv` / `search-scholar` / `search-stacks` / `search-mathlib` / `search-lmfdb` |
| Typed Lean goal / local applicability of a search hit | Installed `lean-search` with workspace pin and search receipts; return checked applications to this coordinator |
| Requested Mathlib/LeanSearch MCP setup | `install-loogle`; actual host tool discovery and smoke test |
| Stacks statement/proof → formalization | `search-stacks` retrieves tagged source; `using-leanpowers` aligns and checks its translation |
| A load-bearing citation or suspect source | `track-down-reference` |
| “Write it up” / any `.tex` output | `using-latexpowers` with the existing plan and evidence; no second intake |
| AI-result produced (statement, counterexample, strategy, reference) | Literature search is mandatory (AI5) — `search-arxiv` / `search-scholar` / `search-lmfdb` / `track-down-reference`; report hits with pinpoint locators and a method comparison, or that the search came back empty |
| Record an AI task's provenance / cost | `update-ai-usage` / `update-tokens` — sole write paths for the repo's master `ai-usage.md` and `tokens.md` |
| Amend powers defaults | `new-powers-policy` — choose explicitly between a repository-local `POWERS.md` override and a global router amendment |
| Formalization requested | `using-leanpowers` with the active plan, source claims and evidence; report a missing installation and continue independent work |

Research output is recorded as it is produced. The repo's `AI-POLICY.md`
(AI-rules; template at
`mathcity/subdomains/repo-docs/templates/AI-POLICY.md`) defines an
**AI-result** as anything from an AI session that would have required
acknowledgement from a fellow mathematician. Each one is logged through
`update-ai-usage` with the model, harness, and skill that produced it, its
derivation account, and its literature-search outcome — including “no hits”
— before it reaches a manuscript. Agents are search and critique tools:
they are cited as software, never as authors and never as the source of a
mathematical claim, and responsibility for correctness stays with the human
authors.

User instructions and repository contracts take precedence over skills. Mathematical and LaTeX policy floors still apply. Missing dependencies or unresolved gates are reported explicitly; neither a plan nor a dispatched agent counts as task completion.

Before planning, read the repository-root `POWERS.md` when it exists and
apply only its `mathpowers` section. It is a repository-local addition or
tightening of the global defaults, not a global skill source. Use
`new-powers-policy` when the user asks to create or amend it, or to change the
global default.
