# Execution, evidence, and completion

Parent: [math-workflow](../SKILL.md).

## Superpowers composition

`using-superpowers` remains the discovery/process bootstrap. For mathematical
and manuscript work, the following domain adapters own phase behavior; use
the software leaves themselves when the task actually changes software.
Do not edit or copy the installed Superpowers skills.

| Process skill | Domain application |
|---|---|
| `brainstorming` | Framing and alternative proof/section strategies in `planning.md` |
| `writing-plans` | Claim/section table, file ownership, evidence and validation in `planning.md` |
| `subagent-driven-development` / `executing-plans` | Bounded tasks, inspect returns, review and integrate; execute sequentially when delegation is unavailable |
| `dispatching-parallel-agents` | Independent research or proof obligations with disjoint scratch outputs |
| `test-driven-development` | For code, follow the actual skill; for mathematics, challenge claims with examples and counterexamples, then prove them. Passing examples is not proof. |
| `systematic-debugging` | Find the first unjustified inference or reproducible build failure; isolate cause before repair |
| `requesting-code-review` / `receiving-code-review` | Check task conformance and mathematical quality, adjudicate feedback against evidence; manuscript reports use `referee-report` and `revise` |
| `verification-before-completion` | Read fresh evidence before claiming success; proof review and compilation are separate checks |
| `using-git-worktrees` / `finishing-a-development-branch` | Isolate conflicting edits when warranted; finish authorized integration only. Never require a branch or commit for a proof lookup. |
| `writing-skills` | Relevant when changing this package, not on every research run |

## Roles and handoffs

Use available agents for independently useful work. Assign cheap/fast capacity
to deterministic inventory and metadata retrieval, standard capacity to source
matching and evidence-backed drafting, strongest suitable reasoning capacity
to hard proofs, strategy changes, and independent review of load-bearing
arguments. Specify available model IDs when the harness permits; honor user
choices and budgets. Do not equate file count with mathematical difficulty.
If a selected model/tool is unavailable, report the limitation and use a
permitted capable substitute or return a blocked obligation.

Each worker receives the exact claim, hypotheses, relevant source excerpts
and paths, dependencies, allowed files, deliverable, review criteria, and
budget/stop condition. Return proof/counterexample/gap, evidence locations,
checks performed, and actual model/tool provenance. Workers do not create
new global plans or delegate recursively. Keep one writer for shared `.tex`,
bibliography, and ledger files; parallel workers own separate scratch paths.

For heavy proving, read pack `subdomains/proof-assist/PROVERS.md` and verify
actual execution capability: listed Fable skills alone do not establish a
working Fable backend. Follow its Fable pipeline when callable, otherwise
its `frontier-dump` path. If neither runs, report the missing backend; do not
invent a dispatch or label local reasoning as an external prover run.
Bounded local reasoning may continue if consistent with the owning leaf.
Record actual usage or “unavailable”; never estimate telemetry as measured.

The coordinator examines each result, checks hypotheses/dependencies, and
resumes the next authorized phase even when a leaf ends with recommendations.
Run independent obligations in parallel; dependent claims wait for evidence.
An unsuccessful attempt triggers diagnosis and a changed approach. Use the
plan's budget; absent one, reassess after two materially distinct failed
approaches and record the next strategy or exact blocker. Do not loop on
unchanged attempts, silently weaken X, or declare a theorem impossible merely
because time expired. A timed-out run is incomplete, with elapsed time and
unfinished scope; warn before an imposed deadline.

## Evidence and review

Read and reconcile the ledger under pack `subdomains/repo-docs/LEDGER.md`:
spot-check the prescribed sample and every touched claim against live source;
rescan affected files on mismatch. A missing/deleted ledger is rebuildable.
Do not erase live mathematical content to make it match a stale cache.

For each proof, check exact target and whole argument: assumptions, reductions,
dependency closure, edge cases, circularity, and source applicability. Invoke
`doubt` on the exact claim/proof with proof-level capacity for hard claims.
Independent work may continue meanwhile. Before promotion or proof-only
completion, collect and adjudicate its result. Save verdict/findings with
claim ID, statement/hypotheses, proof version, reviewer provenance, and date
in the evidence directory; link the ledger's `doubt` column. Changed claims
or material proof edits invalidate review. Pending review is incomplete;
do not stop its workers as routine cleanup.

SOUND means the recorded argument survived that review; it is not a substitute
for a complete proof. WEAK/SUSPECT returns to repair or remains unresolved.
If independent review is unavailable, label self-review honestly; do not
manufacture a SOUND record or complete a promotion requiring one.
Run `contradiction-check` before harvest/promotion; conflicting claims halt
the affected operation pending an explicit resolution, not silent supersession.

Preserve the backend's report and usage artifacts; normalize actual evidence
into the ledger's six statuses. `proved` requires a complete checked argument;
`imported` requires a verified source; `computational` does not certify a
universal statement; `conditional` names unresolved assumptions; `conjectural`
has no proof; `refuted` needs a verified counterexample.

## Manuscript return

All `.tex` output, including indirect suggestions from research leaves,
returns through `using-latexpowers` and pack `subdomains/latex/WRITERS.md`.
Use the user-named, declared destination or the declared notes-tier file.
For research-file synthesis, [synthesis.md](synthesis.md) owns the two review
stages and integration; its default is `notes.tex`, subject to these contracts.
If none exists, prepare the layout/init proposal and request only the needed
approval; do not create an undeclared `notes.tex` or a competing manuscript.

For `using-latexpowers prove X`, produce the declared-target artifact even if proving
is unresolved or backend-blocked: `rapid-prototype` for a short conjecture
stub; `write-proposition` after proof gates. The plan chooses ordering.
A stub records a question, not SOUND promotion. Record refutations honestly,
never as proofs of X. If writer gates block the artifact, name the conflict
and retain the draft in scratch as incomplete.

Honor definition-before-statement LX10, human-marker protection, tagged
edits, verified citations, and the repository's proof-detail requirements.
Repo contracts and policy floors govern; if a leaf cites a missing or obsolete
rule, read current policy, report the mismatch, and resolve it before relying
on the rule. Requested referee revisions retain their owning leaf's authorized
revision-copy exception; ordinary writing stays in the canonical destination.

## Finish and clean up

Use `verification-before-completion`. Inspect actual files, reconcile the
plan's deliverables and open obligations, and verify referenced evidence exists.
Proof validation covers logic and sources. LaTeX validation uses the declared
root/build recipe plus `check-latex`, `check-style`, `check-labels-and-refs`,
and `check-citations` on the affected scope; use `check-layout` after file
changes and `check-latex-hygiene` for applicable current LX rules. Resolve
findings within authorization; report unavailable tools or checks as NOT RUN,
never passing. A clean build does not prove a mathematical statement.

Update claim locations, dependencies, statuses, and review links. Complete or
leave open the corresponding tracker work truthfully. Preserve proof reports,
failed approaches, sources, reviews, usage records, and the plan needed to
resume. Stop finished run-owned workers/processes; remove only run-owned,
disposable artifacts after checking they are not evidence or user work.
Editorial stripping belongs to `garbage-collect` and its concrete approval
gate. Preserve human comments/tags. Remove a task-created worktree only after
checking it is clean and its work/evidence is preserved; retain branches with
unintegrated work and never infer staleness from age or a clean status alone.

Report what was proved/refuted/unresolved, where artifacts landed, validation
and review results, remaining gaps, and cleanup performed. A completed plan,
stub, or background dispatch alone never completes the proof request.
