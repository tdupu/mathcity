# Execution, evidence, and completion

Parent: [math-workflow](../SKILL.md).

## Superpowers composition

`using-superpowers` bootstraps process; these adapters own math/manuscript phases.
Software changes use software leaves; never edit/copy installed Superpowers.

| Process skill | Domain application |
|---|---|
| `brainstorming` | Frame/compare strategies in `planning.md` |
| `writing-plans` | Claims/sections, ownership, evidence/checks in `planning.md` |
| `subagent-driven-development` / `executing-plans` | Bound tasks, inspect/review/integrate; sequential if needed |
| `dispatching-parallel-agents` | Independent obligations, disjoint scratch |
| `test-driven-development` | Follow for code; challenge math with examples/counterexamples, then prove. Examples are not proof. |
| `systematic-debugging` | Isolate first unjustified inference or reproducible build failure before repair |
| `requesting-code-review` / `receiving-code-review` | Check conformance/math against evidence; manuscripts use `referee-report` / `revise` |
| `verification-before-completion` | Fresh evidence; proof review and compilation are separate |
| `using-git-worktrees` / `finishing-a-development-branch` | Isolate conflicts, finish authorized integration; no branch/commit for proof lookup |
| `writing-skills` | Package changes only |

## Roles and handoffs

Use cheap/fast inventory, standard sourcing/drafting, strongest suitable reasoning
for hard proofs/strategy/review. Honor user models/budgets;
record actual model/tool IDs and measured usage or "unavailable". Estimates are
not telemetry; file count is not proof difficulty.

Workers receive claims/hypotheses, sources, dependencies, allowed paths, outputs,
review criteria and limits; return proof/refutation/gap, evidence, checks and
provenance. No global replanning/delegation except Fable forks below. Use one
writer for `.tex`, bibliography and ledger; keep parallel scratch disjoint.
The coordinator checks returns/dependencies and resumes authorized phases;
dependent work waits for evidence.

### Backend eligibility

Read pack `subdomains/lean/PROVERS.md` for heavy proving. Before prompts/dispatch, verify callability, models, isolation, child
permissions, deadlines and every initial write path: package, responses, dump,
contradiction report and accounting/master files. Resolve paths against permitted
roots. Fixed `~/Documents/FABLE-PROMPTS/<slug>/` is not permission; change roots
only with a supported backend override. Never write incompatibly then relocate.

Fable needs a fresh isolated executor whose first substantive act is execution:
load primer/sources once, enumerate filenames without assertion bodies, fork all
questions together before reading responses. Only this executor may spawn these
one-level question workers; they cannot delegate. Stricter harness bans still
apply. The coordinator launches the required clean, non-fork harvester with paths,
fiction disclaimer and no inherited priming/answers. Other child dispatches,
including prompt scaling/accounting, return to the coordinator. Preserve pipeline
verification/artifacts.

If ineligible, use a permitted compatible `frontier-dump` or leaf-permitted local
attempt; absent both, trigger the error below. An explicitly required backend
remains unmet if unavailable; label supplemental attempts accurately, never as
execution of that backend.

### Limits and deadlines

Persist a finite run-wide strategy allowance in the active plan before attempts
(default two slots), with allocations, attempt IDs and used/remaining counts.
Each attempt, question fork, retry/resume or review-triggered repair
reserves a slot and finite work/time cap before starting. New gaps, rewording,
retries and repeated reviews share that total, never reset it. Only explicit
authorization increases it, retaining prior spend. Reviews retain their own
bounds. Diagnose inconclusive attempts and change strategy; infrastructure resumes
may reuse evidence but cost a slot. Exhaustion triggers the failure gate.

Record deadlines as absolute times: imposed limits are hard, explicit
estimates/targets advisory. Warn before overrun. For hard limits, record a
checkpoint/stop time reserving cancellation and handoff time before expiry.
Stop dispatch unless attempt, required harvest/review and that reserve fit.
Bound each wait by 60 seconds and time until the recorded stop.
Checkpoint and stop/cancel run-owned workers before expiry; preserve evidence
and usage. Record IDs, last checkpoint and cancellation acknowledgement.
Unconfirmed cancellation means "possibly active": alert the user, block dependent
integration and retain its files. Backends unable to honor hard limits are
ineligible. At expiry with unfinished work, report **ERROR — deadline_exceeded**,
elapsed time and unfinished scope separately from math/backend outcomes;
expiry proves no impossibility.
An advisory miss needs a warning/revised estimate; continue within the same
allowance without automatic cancellation or `deadline_exceeded`.

## Undetermined mathematics is work, not a disposition

Send in-scope undetermined claims, gaps, conflicting hypotheses and review findings
to `using-mathpowers` in the active plan with exact question, selected evidence
and dependencies; do not restart intake. Execute and consume proof, refutation
or source verification under the eligibility/limits above. A prompt, "unknown"
or stub is insufficient. Apply the gates below and revisit dependencies.
Never silently weaken, omit or defer required results.

If resolution cannot finish, immediately emit visible **ERROR — mathematical
resolution incomplete** to user and coordinator: obligation, attempts/evidence,
reason, blocked dependents and next action/decision. Keep it in the run record
and handoff. Stop affected promotion/integration except the explicit partial-stub
path below; independent work is explicitly partial. Exhaustion is not refutation;
deadlines use `deadline_exceeded`.
Unavailable review/build/source-audit checks need their own visible blocked
gate and owner/action; reasoning cannot replace them. Pending adoption
of a checked result is not math failure.

## Evidence and review

Reconcile the ledger under pack `subdomains/repo-docs/LEDGER.md`: spot-check its
prescribed sample and every touched claim against live source; rescan affected
files on mismatch. Rebuild missing ledgers; never erase mathematics to fit a cache.

Check each whole proof: exact target, assumptions, reductions, dependencies,
edge cases, circularity and source applicability. Invoke `doubt` on the exact
claim/proof with proof-level capacity for hard claims. Collect and adjudicate
before promotion/proof-only completion. Save verdict/findings, claim ID,
statement/hypotheses, proof version, reviewer provenance and date in evidence;
link the ledger's `doubt` column. Changed claims/material proof edits invalidate
review. Pending review is incomplete; independent work may continue. Do not
stop review workers as routine cleanup; hard deadlines use the limits above.

SOUND is a surviving review, not a complete proof. WEAK/SUSPECT requires repair
or unresolved status. Without independent review, label self-review honestly;
never manufacture SOUND or complete a promotion requiring it.

Run `contradiction-check` before harvest/promotion. Conflicts halt it;
preserve both claims and surface the report. Authorized mathematical investigation
permits scratch `using-mathpowers`/`doubt` work despite
the leaf's no-auto-investigation default, within the same allowance. Record
evidence/proposed resolution; never edit either side or declare a canonical winner.
Supersession, retraction and adoption of compatibility rulings remain human acts.
If checked evidence resolves it, report "math resolved; awaiting human adoption";
pending adoption warrants neither retries nor math-failure alerts.
Resume the refused operation only after that decision and proof/writer gates.

Keep backend reports/usage; normalize evidence to six ledger statuses:
`proved` needs a complete checked argument; `imported`, a verified source;
`computational` certifies no universal statement; `conditional` names unresolved
assumptions; `conjectural` has no proof; `refuted` needs a verified counterexample.

## Manuscript return

All `.tex`, including research-leaf suggestions, returns through
`using-latexpowers` and pack `subdomains/latex/WRITERS.md` to the user-named,
declared destination or notes tier. [synthesis.md](synthesis.md) owns presentation
reviews/integration; its `notes.tex` default requires declaration. If absent,
propose layout/init for needed approval; never create a competing or undeclared
manuscript.

For `using-latexpowers prove X`, use `write-proposition` after proof gates.
Failed/incomplete resolution authorizes no canonical edits or automatic
conjecture stubs. Keep an unresolved stub in permitted scratch using
`rapid-prototype` content discipline, without canonical execution/postamble.
Only an explicitly user-requested partial stub may reach the declared target
through writer/adoption gates; it is neither SOUND nor proof/synthesis completion.
Report refutations honestly; name blocked writer gates and retain incomplete
scratch drafts.

Honor LX10, human markers, tagged edits, verified citations and repository proof
detail. Resolve/report missing or obsolete leaf rules against current policy
before use. Referee revisions retain their authorized revision-copy exception;
ordinary writing uses the canonical destination.

## Finish and clean up

Use `verification-before-completion`: inspect files, plan deliverables/open
obligations and evidence paths. Proof validation checks logic/sources; LaTeX
uses the declared root/build recipe, `check-latex`, `check-style`,
`check-labels-and-refs`, `check-citations`, `check-layout` after file changes
and `check-latex-hygiene` for applicable LX rules. Resolve authorized findings;
unavailable checks are NOT RUN, never passing. A clean build proves no theorem.

Update claim locations, dependencies, statuses, review links and tracker work
truthfully. Preserve proofs, failed approaches, sources, reviews, usage and
resumable plan. Stop finished run-owned workers/processes; remove only run-owned
disposables verified not evidence/user work. Editorial stripping uses
`garbage-collect` and its concrete approval gate; preserve human comments/tags.
Remove task-created worktrees only when clean and work/evidence is preserved.
Retain unintegrated branches; age or clean status alone never establishes staleness.

Report claims proved/refuted/unresolved, artifacts, checks/reviews, gaps/cleanup.
A plan, stub or dispatch alone never completes the proof request.
