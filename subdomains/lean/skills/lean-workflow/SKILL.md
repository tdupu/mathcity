---
name: lean-workflow
description: Use when coordinating or resuming a multi-step Lean formalization, manuscript-to-Lean translation or combined Lean maintenance request.
---

# Coordinate the Lean phase

Retain one coordinator, user scope, permissions, plan, claim IDs and evidence
across powers. Load `using-superpowers` once. An active math/LaTeX workflow
receives this bounded phase's artifacts; do not restart intake/brainstorming.
Bounded workers follow their leaf briefs.

Resolve installed skills by plain/plugin-qualified name; read files if no Skill
tool. Verify required resources before each phase.
Optional LSP/search CLI fallbacks: [tools.md](references/tools.md).
Mathlib MCP/Stacks retrieval: [search-tools.md](references/search-tools.md).
Informal proofs are source claims, never compiler certificates. Report exact
missing peers; block only their operations, never imply they ran. Standalone
Lean leaves need no Mathcity, remote search or manuscript plugin.

1. **Frame/resume.** Read repository contracts, actual source, current work and
   [evidence.md](references/evidence.md). Reconcile live artifacts and stale
   evidence. Record exact selected claims, output paths and validation targets.
   A lookup/audit needs a short plan; multiple claims need the repository's
   declared plan location, otherwise dated `ai/` scratch. Reuse its task tracker.
2. **Prepare.** Plan-only: locate/read workspaces, record setup/definition
   obligations, and keep planning probes in authorized scratch. With execution
   authorization, `lean-project` selects/creates the workspace and `lean-doctor`
   records its baseline. `lean-extract-claims` inventories scope;
   `lean-design-definitions` chooses representations; only authorized execution
   invokes `lean-define`.
3. **State and plan.** `lean-align-statement`, `lean-search` and `lean-decompose`
   produce exact targets and an ordered obligation graph. Read
   [source-map.md](references/source-map.md). Compile planned applications;
   signature skeletons remain STATED. A plan-only request stops here.
4. **Execute.** `lean-prove` handles ready obligations and `lean-diagnose` actual
   failures. Carry mathematical gaps to `using-mathpowers` under the same claim
   ID, then resume when evidence returns. Each loop must change the goal,
   evidence or plan; report an impasse instead of repeating failed attempts.
5. **Finish.** `lean-verify`, `lean-fidelity` and `lean-review` check the current
   artifacts. Resolve findings; use `lean-status` for scoped completion. Requested
   manuscript prose goes through `lean-unformalize` and `using-latexpowers` with
   the checked statements and assumptions, preserving the existing plan.

For maintenance, execute only the selected router leaves and their relevant
baseline/final checks. Keep one writer per file. Style, golf, generality and
profiling are distinct; avoid universal cleanup loops.

Superpowers supplies process and evidence discipline; mathematical obligations
replace software test templates. A failed proof is evidence to retain, not code
to delete to satisfy a ritual. End-to-end authorization covers routine reversible
work; user decisions that change claim meaning/scope and external side effects
keep their own boundaries. Neither delegation nor a plan is completion.
