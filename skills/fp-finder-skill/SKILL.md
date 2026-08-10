---
name: fp-finder-skill
description: Fixed-point convergence engine for SKILL.md files. Every accepted revision must be strictly shorter (per-file) AND still APPROVING per critical-review, with a factoring escape valve (new sibling whose baseline is bounded by chars moved from a parent that must itself strictly shrink) and a mutual-approval termination capped at N_max iterations. Designed to be dispatched from coordinate-review when the artifact is a SKILL.md, after generic FP loops on SKILL.md files grew unboundedly without converging. Use when you have one or more SKILL.md files and want to iterate them to a converged, brief, approved fixed point.
---

# fp-finder-skill

A SKILL.md-specialized fixed-point engine. Every accepted revision must be **strictly shorter per-file** AND **still APPROVING** per `critical-review`. Termination is forced by per-file char-count decrease (Rule a), a parent-shrink + sibling-bound rule on factoring (Rule b), mutual approval, or an `N_max = 8` cap. `N_max = 8` is a guard against runaway iteration; longer-than-8 runs indicate a structural problem the loop alone won't fix and should escalate.

**Char-count is a complexity proxy; APPROVING is the quality floor.** A revision that is shorter but loses APPROVING does not count, so `rm`-style gaming fails: strip the body, the critic rejects, the loop returns the previous best. Per-file (not total-tuple) is the rule everywhere; factoring may grow the tuple, but each file individually still shrinks.

## You are the driver

You — the agent invoked as `fp-finder-skill` — execute Steps 1–4 below, spawn the critic and revisor subagents, compute char-counts yourself, and decide the verdict on every gate.

## Inputs

- **artifact** (required): a JSON array of one or more SKILL.md paths, or a single path string.
- **reviewer_persona** (optional): critic lens. Default: "Skeptical first-time reader of skill files."

## State

- `current[path] = (text, wc_c)` — latest accepted state per path. Initialize from inputs with `wc_c = wc -c <path>`.
- `best[path]` — shortest version of `path` that has ever achieved APPROVING; absent if none.
- `iteration N`, starts at 1.

All char-counts are computed by you via `wc -c <path>`. The revisor's self-report is reference only.

`normalize(text)` strips trailing whitespace per line and collapses runs of blank lines to one. Used in the "delta is not whitespace-only" check.

## Subagent dispatch

Spawn subagents via the Task tool (`general-purpose` on Claude Code; equivalent dispatch primitive elsewhere). If the host environment lacks a dispatcher, run critic and revisor inline as separate prompts in the same session, one after the other. For each subagent skill (`critical-review`, `revise-artifact`), locate the file once via `ls <repos-root>/agent-skills/skills/<name>/SKILL.md || ls ~/.claude/skills/<name>/SKILL.md`, read it, strip the YAML frontmatter, and inline the body in the subagent prompt with the artifact text and any iteration context.

**Tuple aggregation.** For tuples of length > 1, spawn one critic per path. The tuple verdict is APPROVING iff every per-path verdict is APPROVING; otherwise the union of action items (tagged by path) is forwarded to the revisor.

## Loop

**Step 1 — Critic.** Spawn `critical-review` per path; aggregate.

- APPROVING and `N == 1` (initial input never been promoted): for each path, set `best[path] := current[path]`, then go to Step 4 with `initial_input_approved = true`.
- APPROVING and `N > 1`: go to Step 4.
- NEEDS-REVISION: collect action items; go to Step 2.

**Step 2 — Revisor with monotone gate.** Spawn `revise-artifact` with the action items AND this **gate instruction verbatim**:

> Your revision must satisfy one branch per modified or new file:
>
> (a) **Shrink-in-place.** For each pre-existing file you modify, strictly fewer chars than that file's input version, and the delta must not be whitespace-only.
>
> (b) **Factor.** Move a self-contained chunk out of one pre-existing **parent** file into a NEW **sibling** file. The parent MUST end up strictly shorter than its input version (no "factoring" without parent-shrink). Per parent in this iteration, the **sum of sibling sizes** must not exceed the chars removed from that parent (so multiple siblings from one parent share a single budget). Per individual sibling: count only the body (everything after the YAML frontmatter) against the budget; the frontmatter is unavoidable overhead and is free.
>
> You may combine (a) and (b) across files. Never pad, never copy-shift, never rename to inflate baselines. Report `chars_removed_from_parent` and `sibling_body_wc_c` for every Rule-(b) sibling so the driver can verify.

**Step 3 — Validate then re-critique.** You re-count every modified or new file with `wc -c`. Reject the revision and terminate (return `best`) if any check fails:

| Check | Applies to | Rule |
|---|---|---|
| Strict decrease | every modified pre-existing path | `wc_c(new) < current[path].wc_c` |
| Delta-not-whitespace | every modified file where `wc_c(new) < wc_c(old)` | `normalize(new) != normalize(old)` |
| Sibling-budget | every parent that produced sibling(s) this iteration | `sum(wc_c(sibling_body)) <= chars_removed_from_parent` |
| Parent-shrunk on factor | every iteration with one or more new siblings | every named parent satisfies the Strict-decrease check above |

If all pass, spawn `critical-review` on the new tuple. If APPROVING: promote each changed/new path into `current`; update `best[path]` whenever shorter or absent. Increment `N`. If `N > N_max`, go to Wrap-up. Otherwise return to Step 1. If NEEDS-REVISION: revision **fails the floor** — discard and terminate (return `best`).

**Step 4 — Mutual-approval termination.** The critic has approved. Spawn the revisor exactly once with this prompt template (no variant phrasings):

> The artifact tuple below has been approved by the critic. Either:
> - Answer **NO** if you cannot identify a strict-shrink-or-factor change that would **materially** improve clarity, correctness, or completeness (your contract is to answer NO when no material improvement exists), OR
> - Provide a concrete revised tuple as a Step-2 revisor would: state action items you want to address, then output the revised file content(s) and any factoring `chars_removed_from_parent` / `sibling_body_wc_c` numbers. Do not answer YES without a concrete revision payload.
>
> [current tuple]

NO → mutual approval; return `best`. Concrete revision → treat as Step 2 output (re-validate in Step 3) and continue.

## Termination

Every accepted revision strictly decreases at least one file's char-count (Rule (a) decreases the modified file; Rule (b) decreases the parent via the Parent-shrunk-on-factor check). Char-counts are non-negative integers, so per-file budgets sum to finite. Factoring introduces new siblings, but the per-parent sibling-budget bounds the sum of sibling bodies by chars-removed from that parent — so the total system-wide body chars never grow more than they shrank on the same iteration. Frontmatter overhead per sibling is constant; total siblings created across all iterations is bounded by initial total parent body chars divided by the smallest meaningful factor, which is finite. `N_max = 8` is the explicit backstop.

## Returns

- `best[path]` present: shortest APPROVING version of that path.
- `best[path]` absent (initial input never APPROVING, or a revision lost the floor before any APPROVING pass): return the path's initial text with note `"no improvement confirmed."`
- `initial_input_approved = true` at termination: prefix `best` with note `"converged at N=1; initial input was already a fixed point."`
- Factored-out parents: their `best` is the APPROVING version of the now-narrower parent.
- Siblings created in an iteration whose re-critic then returned NEEDS-REVISION: omit from `best`; return their text-on-disk with note `"sibling created but iteration discarded; review manually."`
- `N_max` hit: prefix wrap-up with `"stagnated at N_max iterations; returning best so far."`

## Pitfalls

- **Padding gaming.** Step 3's delta-not-whitespace + the critic's bloat detection together defend against whitespace and meaningless-token padding.
- **Spurious factoring.** A sibling with no consumer is dispatch overhead. The factored chunk must be self-contained, the parent's narrowed `description` must still cover it, and the parent should reference the new sibling.
- **Revisor lying about chars.** You always re-count via `wc -c`. The revisor cannot evade.
- **Char-count rewards terseness over examples.** Concrete examples may lose to abstract prose. The APPROVING floor protects against this: load-bearing examples removed → critic blocks → revision loses the floor.
- **The proxy is not the goal.** Minimize char-count *subject to* APPROVING; never for its own sake.
