# Math and LaTeX workflow refactor

Parent: [skills index](../../../README-skills.md).

This is the design and validation record for the router refactor, not a task
tracker. The implementation request authorizes the refactor and its review;
the subsequent `claude-commit` request authorizes commit, pull, and push.
Live-city deployment remains outside this change.

## Purpose and triggers

`using-mathpowers` carries mathematical work from framing through verified outcome;
`using-latexpowers` adds manuscript stewardship and the requested stub/write-up.
Both invoke `using-superpowers` and the same `math-workflow` coordinator.
The shorter `using-math` and `using-latex` names remain thin aliases. Research, proof, source
verification, writing, audits, and repository-contract leaves remain owners
of their operations.

Representative requests are “prove X,” “what is known about X,” “find something
to prove,” “attack the skeleton,” “are you sure,” “write this up,” “referee our
section,” “we received a report,” and “prepare for submission.” Proving through
the LaTeX entry point includes a manuscript artifact at the declared target.

## Boundaries and baseline

Assigned leaf workers do not restart the router. Formalization is a separate
workflow. Read-only and plan-only requests preserve those boundaries; broad
end-to-end requests continue through authorized work without repeated prompts.

Two pre-change router samples and five fresh no-guidance samples were read.
They generally preserved mathematical honesty, but did not reliably produce
an explicit claim/section plan or persist a version-bound review record and
complete cleanup. Thus the observed failure is **omitted required structure**,
not primarily disobedience: add a positive workflow and required plan fields,
not a collection of invented rationalization warnings.

One representative baseline said: “I would keep files within the authorized
project locations and integrate useful agent findings.” This leaves artifact
ownership, review persistence, and disposal unspecified. Another said “preserve
the proof and verification evidence at stable project paths” without supplying
a plan that names those outputs and their dependencies. Samples were workflow
simulations, not live prover/backend runs.

## Architecture, leaves, and gate

Two short routers preserve the full dispatch surface. One cross-domain process
leaf owns a single run context, loading framing/research/planning and execution/
review/finish references. Shared state prevents math↔latex recursion. Before
any dependent operation, resolve the repository contract and verify the needed
leaf/backend. Missing resources are reported explicitly, while independent
authorized work continues.

The dispatch tables carry observable predicates, competing examples, and
existing human gates. Checks precede affected writes; expressed doubt outranks
a bare status answer; contradictions block dependent promotion; variants are
triaged before affected editing. New definitions precede theorem statements.

The claim ledger is reconstructible metadata, not mathematical authority.
Persist actual `doubt` results against the exact proof version. Use callable
backend detection, not mere skill-list membership. Distinguish conjectural
stubs from proved promotion. Preserve existing policy/leaf gates and user
changes, including LX10, rather than rewriting unrelated skills.

## E — alternatives / check-zero

| Resource or design | Coverage | Decision |
|---|---|---|
| Existing routers and research-SOH recipe | Domain routing and literature sweep, but no shared end-to-end process | Adapt; retain every use case and redirect the old recipe |
| Superpowers bootstrap and process leaves | Discovery, framing, concrete plans, task execution, review, evidence and finishing | Compose/adapt domain semantics; do not copy or alter upstream skills |
| Duplicate full process in both routers | Covers the request but creates two maintenance surfaces | Rule out; one shared process |
| New proof/writing engines | Existing PROVERS, writers and review leaves already own these operations | Rule out; no reinvention |

Wheel verdict: adapt existing routing/process; the remaining gap is a shared
mathematical orchestration contract. Repository and installed-skill searches
found no existing leaf that owns this full handoff. Beads search found no
matching task; task creation was blocked by its remote-backed database schema
adoption gate. No database migration or destructive bootstrap was attempted.

## Source research

The [Superpowers README](https://github.com/obra/superpowers) describes automatic
skill discovery and staged work with review. The creator's
[initial explanation](https://blog.fsck.com/2025/10/09/superpowers/) shows how
the bootstrap replaces repeated prompting and how realistic pressure tests
expose missing discipline. His
[Superpowers 5 discussion](https://blog.fsck.com/2026/03/09/superpowers-5/)
explains bounded subagent work, capability selection, and protection against
recursive orchestration. [Simon Willison’s contemporaneous reading](https://simonwillison.net/2025/Oct/10/superpowers/) highlights the accumulated process techniques and selective loading of skills. These motivate the shared process; they are not
evidence that any mathematical claim has been proved.

## File scope and portability

Canonical source remains in mathcity: the original subdomain router directories,
the parent-pack `math-workflow` directory, compatibility files at the shorter-name
paths, README/index updates, and behavioral scenarios. Agent-skills exposes
the new directories as relative symlinks, also discovered through the existing
user-scope skill-directory links. No materialized copies or vendor edits.
Current installed pack/root resources are resolved explicitly; research-repo
paths are kept distinct. This is repo-side, outside-agent work, with no fleet
dispatch, configuration changes or city deployment.

Plan-hygiene review: canonical ownership, one source, portable links, README
updates, explicit errors, bounded reviews, and preserved existing changes
cover the applicable P1–P7 concerns. New live-city exposure is a deployment
step outside this change; do not claim it was tested. No new repeated CLI
operation or consumer transport is introduced.

## Load plan and validation contract

Routers hold predicates and dispatch; the shared process leaf holds phase
control. Each reference is loaded for its phase. No session-start hook or
global settings change is needed. Repository/user instructions outrank skills.

The [behavioral scenarios](../../../tests/math-workflow/scenarios.md) exercise
time pressure, sunk cost, misleading authority, unavailable infrastructure,
cross-routing, and cleanup. Five fresh samples per scenario must satisfy all
required outcomes. They test operational decisions, not external provider
execution. The eight skill/reference files then receive tuple-level fixed-point
review in groups no larger than five: per-path critics, strict per-file byte
decrease for accepted edits, and explicit critic/revisor mutual approval.

Final validation also checks frontmatter, link/resource resolution, retained
leaf coverage, index entries/counts, privacy/secret scanning, and source/sink
agreement. The completed run's counts and limitations are recorded below.

## Validation results

All eight skill/reference files reached mutual-approval fixed points. The five
core files converged at iteration 2 after one accepted revision; the three
compatibility files were fixed points at iteration 1. Every final per-path
critic returned APPROVING with zero blocking, major, or minor findings, and
each tuple's final revisor answered NO to the prescribed material-improvement
question. No revisions were discarded. The core's second critic step reused
passed reviews on byte-identical content; the mandatory final revisor still
ran. The total decreased from 25,823 to 25,677 bytes; every modified file
strictly shrank with a substantive change.

Five fresh-context samples each exercised scenarios A, B, and C after the
fixed-point changes. Coordinator inspection scored all 15 responses PASS.
They retained pending reviewers, rejected stale/weaker proof evidence,
preserved human markers and source records, produced gated conjecture drafts,
and reported unavailable backends without inventing execution. These are
operational simulations, not live theorem-proving or manuscript-editing tests.

Structural checks cover 13 package files, five skill frontmatters, 23 local
links, all 39 named skill references from the original routers/recipe, and the
174-entry skill index. The leaf-coverage review checked dispatch predicates,
competing cases, and existing gates in addition to name retention. The index
also corrects its pre-existing one-skill undercount. Final installation checks
compare reviewed payload hashes and resolve all three relative discovery
links; the installer refuses concurrent destination changes.

No live-city installation, provider invocation, mathematical correctness
certification or database migration is included. Beads task
creation remained blocked by the existing remote-backed database adoption
gate; implementation and review did not alter that database.

## Naming preference and publication

The owner subsequently chose `using-mathpowers` and `using-latexpowers` as
the primary names and invoked `claude-commit` to publish the changes. The
full routers now live at those original names; the shorter names delegate
to them. Shared process, leaf routing, and evidence requirements are unchanged.
The fixed-point and simulation results above precede this naming-only swap;
a mechanical equivalence check verifies the final skill bodies modulo names,
with frontmatter, links, alias targets, and documentation checked again.
