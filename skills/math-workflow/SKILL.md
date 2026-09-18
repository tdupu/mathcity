---
name: math-workflow
description: Use when a mathematical research or manuscript task needs framing, research, planning, coordinated execution, proof review, or completion bookkeeping; also when using-mathpowers or using-latexpowers starts or resumes work.
---

# Math and manuscript process

Required process for `using-mathpowers` and `using-latexpowers`. Load `using-superpowers`
once. This adaptation retains discovery, process-before-action, bounded
delegation, review, and evidence before completion; software templates are
not proof obligations.

## Start or resume

One coordinator owns request, mode, repo, contracts, plan, claims/dependencies,
paths, permissions, and outstanding work. Cross-router calls pass this context
and a bounded phase, returning artifacts without restarting brainstorming.
Leaf workers follow their briefs without recursive orchestration.

Resolve this skill's real installed path and the enclosing mathcity pack root
(contains `pack.toml` and `subdomains/`). All `subdomains/...` references in
this package are relative to that root, not the research repository.
Resolve skills by their installed plain or pack-qualified names. Before a
phase, verify its required skills, files, tools, and backend are accessible.
Report a missing dependency with its exact name and setup action; continue
only independent phases, never pretend the blocked phase ran.

Read the repository's instructions and current artifacts. Reconcile claims
under pack `subdomains/repo-docs/LEDGER.md`; live source records what the
repository says, while proofs and checked sources support mathematical truth.
For manuscript work use pack `subdomains/repo-docs/RESOLUTION.md`.
Adapt every `init-repo-docs` call: preserve existing contracts and declared
paths; draft only missing documents before adoption approval. Never run its
unconditional five-template copy over existing contracts.

## Workflow

1. **Frame, investigate, plan.** Read [planning.md](references/planning.md).
   Complete its mathematical brainstorming and depth selection. Record the
   claim/section plan before production; unresolved mathematics is explicit
   research work, never invented proof text.
2. **Execute and review.** Read [execution.md](references/execution.md).
   Dispatch the router's leaves in dependency order, consume their outputs,
   and continue the authorized request. Review exact claims and versions.
3. **Finish.** Run the same reference's validation and cleanup pass. Return
   evidence, file locations, open obligations, and truthful completion status.

Scale the process: a lookup, audit, or local correction needs a short in-chat
plan; multi-claim research or manuscript construction needs a durable plan.
Read-only requests remain read-only. A plan-only request ends after plan
review; an execution request proceeds through its feasible steps.

Explicit end-to-end requests authorize routine planning, research, delegated
work, and reversible edits in their stated scope. Do not repeatedly ask to
continue. Ask only for missing choices that materially change the claim,
destination, or scope, and for unsatisfied explicit gates. Repository policy
adoption, acceptance of a referee report, and destructive editorial stripping
retain their owners' approval rules. Respect existing authorization.

Use the repository's task tracker; the mathematical ledger is not a competing
task system. Do not commit, push, publish, modify policy, or delete evidence
merely because a generic finishing skill includes those steps.
