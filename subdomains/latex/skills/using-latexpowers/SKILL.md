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
| “What does this proof use?” | `resolve-dependencies` |
| ACCEPTED report to apply | `revise` — item-to-edit map |
| “Referee our section” | `referee-report` — read-only review |
| Received referee report | `triage-referee-report` or manual astra/fable route — preserve the human's choice and authorized revision destination |
| Decision-record audit | `check-adr` |
| “Prep for arXiv” / editorial stripping | `garbage-collect` — approval of the concrete strip set |
| Methods / software / AI disclosure | `write-materials-and-methods` |
| Explicit introduction/abstract request | `write-introduction` — readiness/refusal gates; never volunteer it |
| Amend layout / LaTeX / style / decisions / agent contracts | `new-repo-layout-policy` / `new-repo-latex-policy` / `new-repo-style-policy` / `new-repo-adr-policy` / `new-repo-agents-policy` — human-authorized amendments |
| Amend LX rules | `new-latex-policy` — human-authorized policy change |
| Merge/reorder sections | `merge-latex-sections` is HOLD; report the unsupported operation |

Checks precede affected writes. Definitions, constructions, and new notation precede theorem-class statements (LX10), even without a local ST10. Review statement bodies; compilation alone does not verify this.

User instructions and repository contracts take precedence over skills, subject to LaTeX policy floors. Preserve leaf gates and report unresolved conflicts explicitly.
