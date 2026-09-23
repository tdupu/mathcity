---
name: using-leanpowers
description: Use when formalizing natural-language proofs or manuscripts in Lean, working on .lean files, checking formalization fidelity, maintaining a Lean project or assessing a Mathlib contribution.
---

<SUBAGENT-STOP>
Assigned a bounded leaf task? Follow its brief and evidence gates without restarting orchestration.
</SUBAGENT-STOP>

Invoke `using-superpowers` once; reuse the active coordinator and authorization.
Select the route before its action. Mixed tasks retain one plan: mathpowers owns
informal mathematics, latexpowers manuscript writing, leanpowers formal artifacts.
Missing peers are reported; independent Lean CLI work can continue.

| Observable request or condition | Route |
|---|---|
| Natural-language proof/manuscript → Lean; several phases; resume | `lean-workflow` |
| Add or locate a Lean workspace | `lean-project` |
| Prepare or update a registry (Palomar) manifest | `lean-project` fixes its path, `<workspace>/PALOMAR.md`; submission is a separate, explicitly authorized act |
| Unknown toolchain/build baseline | `lean-doctor` |
| Inventory source claims and gaps | `lean-extract-claims` |
| Choose mathematical representations | `lean-design-definitions` |
| Implement agreed definitions/structures/instances | `lean-define` |
| Translate/check one theorem's full type | `lean-align-statement` |
| Find a library lemma/instance | `lean-search` |
| Stacks tag/statement/proof needed | `search-stacks`; fallback and formalization handoff in [search tools](../lean-workflow/references/search-tools.md) |
| Prior formalization or named Lean result in Palomar needed | `lean-search`; use the Palomar source route in [search tools](../lean-workflow/references/search-tools.md) |
| Tau Ceti declaration, precedent or roadmap target needed | `lean-search`; use the pinned Tau Ceti route, then `using-taucetipowers` for contribution work |
| Requested Mathlib MCP setup | Installed `install-loogle`; standalone setup/fallback in [search tools](../lean-workflow/references/search-tools.md) |
| Split proof obligations or find prerequisites | `lean-decompose` |
| Prove one aligned Lean target | `lean-prove` |
| Actual Lean error or stalled goal | `lean-diagnose` |
| Check build, target coverage and axioms | `lean-verify` |
| Does Lean express this source claim? | `lean-fidelity` |
| What's formalized, conditional or blocked? | `lean-status` |
| Formatting, names, docs, imports | `lean-style` |
| Simplify an already working proof | `lean-golf` |
| Weaken assumptions or broaden a theorem | `lean-generalize` |
| Slow elaboration or explicit performance request | `lean-profile` |
| Rename, extract or split modules | `lean-refactor` |
| Review formal code and its evidence | `lean-review` |
| Does this belong in Mathlib? | `lean-mathlib-fit` |
| Synchronize a blueprint/dependency presentation | `lean-blueprint` |
| Explain a Lean theorem in prose | `lean-unformalize` |
| Requested Lean/Mathlib version change | `lean-upgrade` |
| Prepare a contribution locally | `lean-prepare-pr` |
| Apply review comments | `lean-apply-feedback` |
| Informal proof/research without formalization | `using-mathpowers` |
| Manuscript-only edits | `using-latexpowers` |

Before planning, read the repository-root `POWERS.md` when it exists and
apply only its `leanpowers` section. It is repository-local and may add or
tighten defaults, but it does not replace global quality floors. Use
`new-powers-policy` when the user explicitly requests either a local override
or a global leanpowers amendment.

For competing routes, establish the baseline, align the claim, then perform the
requested change and its checks. Compilation and source fidelity are separate
gates. Read-only and plan-only requests retain that scope. Generic software work
returns to Superpowers. User and repository instructions outrank these skills.
