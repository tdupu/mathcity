---
name: using-latexpowers
description: Use when working on mathematical manuscripts, notes, .tex files, citations, referee reports, submission cleanup, or repository writing contracts; when proving a claim for notes, planning sections, writing statements, or resolving competing manuscript files. Also accepts using-latex and using-latexpower.
---

<SUBAGENT-STOP>
Assigned a bounded leaf task? Follow that brief and its writer/evidence gates; do not restart the top-level workflow.
</SUBAGENT-STOP>

**First invoke `using-superpowers`, then `math-workflow` in latex mode.** Reuse an active workflow; resolve contracts and dispatch before any edit. Announce the route; non-manuscript work returns to its domain skill.

Latex mode uses `using-mathpowers` for proofs/research and executes the requested declared-target artifact: `rapid-prototype` for unresolved claims, even with a blocked backend; writers for established results. Writer gates apply. Both routers share one coordinator and plan.

## Dispatch

| Situation | Route |
|---|---|
| Missing contracts | `init-repo-docs` via `math-workflow`'s preserve-existing adapter; adoption gate |
| Layout health / “which file is real?” | `check-layout` |
| Undeclared sibling `.tex` | `triage-variants` — authorized per-file disposition before affected writing |
| Style / build / LaTeX hygiene / references / citations | `check-style` / `check-latex` / `check-latex-hygiene` / `check-labels-and-refs` / `check-citations` |
| “Prove X” / research gap / suspect mathematics | `using-mathpowers` for that obligation, then return here for the requested artifact |
| Claim needs a source / suspect cite / verification marker | `track-down-reference`; `clean-citations` for citation-repair proposals |
| Evidenced statement / definition / connecting explanation | `write-proposition` / `write-definition` / `write-remark` |
| Requested stub / discussion-to-skeleton / unresolved X | `rapid-prototype` — conjecture or definition, never a fake proof |
| Scratch computation → notes | `explain-experiment` |
| Computed graph / spectrum / mathematical plot | `generate-graphics` — Sage source, checked data, provenance, rendered preview |
| Existing graphic → explanatory manuscript figure | `add-figure` — verify meaning, caption and reference at the relevant passage |
| Worked case / finite example / counterexample | `write-example`; compose `add-figure` when a graphic explains it |
| “What does this proof use?” | `resolve-dependencies` |
| ACCEPTED report to apply | `revise` — item-to-edit map |
| “Referee our section” | `referee-report` — read-only review |
| Received referee report | `triage-referee-report` or manual frontier/fable route — preserve the human's choice and authorized revision destination |
| Decision-record audit | `check-adr` |
| “Prep for arXiv” / editorial stripping | `garbage-collect` — approval of the concrete strip set |
| Methods / software / AI disclosure | `write-materials-and-methods` — to the repo's `AI-POLICY.md` contract |
| “Is the AI statement right?” / pre-submission disclosure audit | `latex-ai-statement` — per-rule verdict against `AI-POLICY.md` and the trail; routes repairs |
| Record an AI task's provenance / cost | `update-ai-usage` / `update-tokens` — sole write paths for the repo's master `ai-usage.md` and `tokens.md` |
| Amend the repo's AI-usage contract | `new-repo-ai-policy` — human-authorized amendment |
| Explicit introduction/abstract request | `write-introduction` — readiness/refusal gates; never volunteer it |
| Amend layout / LaTeX / style / decisions / agent contracts | `new-repo-layout-policy` / `new-repo-latex-policy` / `new-repo-style-policy` / `new-repo-adr-policy` / `new-repo-agents-policy` — human-authorized amendments |
| Amend LX rules | `new-latex-policy` — human-authorized policy change |
| Merge/reorder sections | `merge-latex-sections` is HOLD; report the unsupported operation |
| Refuted claim / counterexample / failed expectation from prior work | State it as a result (LX11) — `write-proposition` or `write-example` for the refutation, `write-remark` for the intuition it corrects; never drop the claim and its refutation together |
| Rendering prior work into a new document (dump, digest, synthesis, revision, introduction, exposition, merge, handoff) | Carry the input's negative results forward first (LX12); list any excluded finding with its scope reason |

Checks precede affected writes. Definitions, constructions, and new notation precede theorem-class statements (LX10), even without a local ST10. Review statement bodies; compilation alone does not verify this.

Negative results are results (LX11). When the work behind a document refuted a
claim, disproved an expectation, found a counterexample, or showed a proposed
definition ill-posed, that finding is stated in the document as a numbered
theorem-class statement — or, when unproved, as a labelled question or
conjecture — with the expectation it corrects named in the text: "it is
natural to expect $X$; in fact $Y$". Never delete a wrong claim together with
its refutation; the refutation is the surviving result, and in a subject whose
intuition is imported from a neighbouring theory it is often the most valuable
one. Any artifact produced from previous work carries that previous work's
negative results forward (LX12) — before, not after, its positive results —
and records a scope reason for every finding deliberately left out. Both are
document-quality floors: enumerate the evidence trail, match findings to
statements, and report counts; a keyword scan does not discharge them.

AI disclosure is a document-quality floor, not an optional courtesy. The
repo's `AI-POLICY.md` (AI-rules; template at
`mathcity/subdomains/repo-docs/templates/AI-POLICY.md`) governs what any
manuscript must say about models, software, and AI-results, and requires a
master `ai-usage.md` and `tokens.md` at the repository root. Every AI-result
carries a literature search and a derivation account; software—including AI
providers and the workflow skills themselves—is cited like Magma or
SageMath; agents are never authors and never the source of a mathematical
claim.

User instructions and repository contracts take precedence over skills, subject to LaTeX policy floors. Preserve leaf gates and report unresolved conflicts explicitly.
