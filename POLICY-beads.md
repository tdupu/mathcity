# Mathcity Bead Policy

| Field | Value |
| --- | --- |
| Status | Draft |
| Date | 2026-07-12 |
| Decided | the pack owner |
| Applies to | All bead creation, typing, labeling, memory use, and bead removal in the mathcity ecosystem (all rigs, all agents) |
| Consumers | `record-decision`, `gc-recycle-bead`, `remember-this`, `brief-prep`, `create-convoy`, `fan-out`, `catch-no-brainer`, `check-math-bead-hygiene`, `new-math-bead-policy`, `new-beads-policy`, any sweeper/reaper skill, Mayor dispatch |

Governs how beads are typed, how research beads are protected, when knowledge goes into `bd remember` versus a bead, and when an old bead may be removed. Companion reference (non-normative): [README-beads.md](README-beads.md). On conflict with POLICY-POLICY.md, POLICY-POLICY.md wins.

Rule prefix: **BP** (reserved in `mathcity/docs/rule-prefix-registry.md` per PP5.2).

---

## Core definitions

- **Mathematical research bead.** A bead whose work product is NEW MATHEMATICS — exploring a theorem, deriving a formula, proving a conjecture, working through examples. Not time-boxed; may run for months. This is never "investigating technical uncertainty" — it IS the work.
- **Technical investigation (deep-research) bead.** A bead whose work product is KNOWLEDGE ABOUT THE SYSTEM — "why does this fail?", "what does this function do?", "is this approach feasible?". Time-boxed, produces a finding, leads to further work.
- **Old useless bead.** A bead meeting one of the BP4.2 removal criteria and none of the BP4.4 protections.
- **Reaper sweep.** A batch pass that closes old useless beads under the BP4.3 protocol.

---

## Pillar 0 — Pre-creation redundancy gate (BP0.x)

Governs what must happen BEFORE a new bead is created and dispatched via `mathcity.work`. This is the pre-hook that prevents the dispatch queue from accumulating parallel beads addressing the same problem.

- **BP0.1 Redundancy check before dispatch-bead creation.** Before running `bd create` for any bead that will immediately be slung via `mathcity.work` (or otherwise enter the dispatch queue), the creator MUST run `mathcity.new-beads-policy` (alias: `/new-beads-policy`) to check for semantic overlap with existing open beads.

- **BP0.2 Three-verdict system.** The `new-beads-policy` check emits one of three verdicts:
  - **PROCEED** — no meaningful overlap; creation is safe.
  - **MERGE** — an existing bead covers ≥2 of 3 overlap dimensions (problem, scope, goal). Add a comment to the existing bead instead of filing a new one.
  - **DROP** — the problem is already fully covered by an in-progress bead. No action needed.

- **BP0.3 MERGE beats PROCEED when uncertain.** If the overlap is ambiguous, prefer MERGE (add a comment on the existing bead) over filing a new bead. A comment is always lower cost than a stranded parallel bead.

- **BP0.4 xkcd-927 is the test.** The redundancy check is equivalent to running `/xkcd-927` on the proposed bead: "are there already N solutions to this problem?" If yes and N ≥ 1, MERGE or DROP; do not create the N+1 solution.

- **BP0.5 Exemptions.** The pre-creation gate is NOT required for:
  - Beads that are NOT going to dispatch queue (math research beads, epics, convoys, decision records).
  - Beads created by inside workers (gc-managed formulas) responding to a human-approved brief — the brief is the authorization.
  - Emergency hotfix beads filed during an active incident.

- **BP0.6 Hygiene.** `check-math-bead-hygiene` MAY flag a bead as BP0-suspect if it duplicates the title of an existing open bead by >80% lexical similarity. This is a soft flag, not a hard violation (semantic overlap is the test, not lexical).

- **Skill:** `mathcity.new-beads-policy` (at `<mathcity-pack-root>/skills/new-beads-policy/SKILL.md`).
- **Cross-references:** [[mathcity.work]] §Step 0, [[xkcd-927]], [[bead-flight-precheck]] (post-creation pre-sling gate).

---

## Pillar 1 — Bead type selection (BP1.x)

- **BP1.1 Only documented bd types are used.** The canonical set is exactly what `bd create --help` documents: `bug`, `feature`, `task`, `epic`, `chore`, `decision`, `spike`, `story`, `milestone`. No invented types (e.g., `research-journal`) may appear in beads, policy prose, or skill code (cross-ref: dev policy P5.3).
- **BP1.2 task/feature/bug are the standard work types.** `task` is the default for concrete implementation work with acceptance criteria; `feature` for new user-visible capability (implies a PR/merge outcome); `bug` for defects and regressions (implies root-cause + fix, test evidence before close).
- **BP1.3 spike = technical investigation ONLY.** A `spike` bead investigates a technical question about code, infrastructure, or system state. It is time-boxed, produces a finding (in bead notes or a follow-up bead), and leads to further work. Examples: "investigate why decisions/ is empty", "research what bd types are available", "check if Option Z propagates retroactively".
- **BP1.4 Mathematical research is NEVER a spike.** Original mathematical work (theorem exploration, formula derivation, proof work, example computation) is `type: task` or `type: feature` carrying the `[MATH_RESEARCH]` label while ongoing. Mathematical research is not time-boxed and its output is new mathematics, not system knowledge. Typing math research as `spike` is a BP1.4 violation. See Pillar 2 for the completed-research lifecycle.
- **BP1.5 decision = briefs and adjudications.** Briefs are `type: decision` labeled `brief-open` (pending) or `brief-closed` (adjudicated). Recorded adjudications, policy locks, and verdicts are `type: decision` created via `record-decision`. Decision beads are never reopened; follow-up is a new bead (cross-ref: brief-system B2.2, B3.8).
- **BP1.6 epic = grouped work; decompose via convoy.** A large effort spanning multiple tasks/features is an `epic`, decomposed with `create-convoy` + `fan-out`. An epic closes only when all members are terminal (cross-ref: B3.5).
- **BP1.7 chore = maintenance.** Housekeeping with no user-visible change (renames, dep bumps, dead-code pruning). Low-ceremony; usually no brief needed.
- **BP1.8 milestone = release/date markers.** Time-bound goals aggregating epics and features: release markers, conference-deadline targets (e.g., the July 15 public-release target).
- **BP1.9 story is discouraged.** Agile user stories are rarely the right shape here; prefer `feature`. `story` remains legal (it is a documented type) but a new `story` bead should justify why `feature` does not fit.

---

## Pillar 2 — Research bead protection (BP2.x)

- **BP2.1 Ongoing mathematical research carries `[MATH_RESEARCH]`.** Any bead whose work is original mathematics in progress is `type: task` or `type: feature` with the `[MATH_RESEARCH]` label. The label signals: not time-boxed, not eligible for staleness-based reaping (BP4.4), and never reclassifiable to `spike` (BP1.4).
- **BP2.2 Completed reference mathematics becomes a research journal.** When a `[MATH_RESEARCH]` bead completes and its content is a permanent mathematical reference, it transitions to the research-journal state: add the `[RESEARCH_JOURNAL]` label and protect with `bd defer <id> --reason="research journal — ARCHIVED-equivalent, do not close"`. This is the interim ARCHIVED protocol of brief-system B3.7; B3.7's mechanical protections (no `bd close`, sweeper exclusion) apply in full.
- **BP2.3 `[RESEARCH_JOURNAL]` beads are never closed destructively.** Restatement of B3.7 for this domain: any `bd close` targeting a bead labeled `[RESEARCH_JOURNAL]` is a policy violation; batch-closing skills (sweepers, convoy landers, no-brainer executors, the BP4.3 reaper) must exclude beads carrying this label.
- **BP2.4 B3.7's spike-typing step does not apply to mathematical research.** B3.7(a) ("ensure the bead is `type: spike`") was written for investigation-output journals and predates the math-research/tech-investigation distinction. For mathematical research journals, retain `type: task`/`feature` + `[RESEARCH_JOURNAL]` + defer; do NOT retype to `spike`. Technical-investigation journals (spike output worth keeping permanently) remain `type: spike` + `[RESEARCH_JOURNAL]` + defer as B3.7 specifies. (Flagged for reconciliation in the brief-system policy via `new-brief-policy`.)
- **BP2.5 Spike findings that matter get durable homes.** A closed spike's finding must land somewhere durable before close: bead notes on the spike, a follow-up work bead, or a `bd remember` entry when the finding is a persistent fact (Pillar 3). A spike closed with no recorded finding is a BP2.5 violation.

---

## Pillar 3 — Memory policy (BP3.x)

- **BP3.1 Memories are for persistent knowledge, not task state.** Use `bd remember --key <slug> "<content>"` for: persistent facts, design insights, hard-won debugging discoveries, agent identity info. Do NOT use memories for: ephemeral task state, TODO lists, or anything that belongs in a bead's description/notes. Task tracking lives in beads; knowledge that must survive session death lives in memories.
- **BP3.2 The retrieval contract.** Memories are injected at `bd prime` time and retrieved via `bd recall <key>` (exact key) or `bd memories <keyword>` (search). Adjudications are NOT memories — they are decision beads, retrieved via `bd list -t decision`. A fact stored only in a session transcript or a scratch file has not been remembered.
- **BP3.3 Keys are stable slugs.** Memories use explicit `--key` slugs (kebab-case) so `bd recall` is deterministic. Updating a memory reuses its key (in-place update) rather than creating a near-duplicate under a new key.
- **BP3.4 Bead-vs-memory routing.** If the content is actionable (someone should DO something) → bead. If the content is a fact/insight future sessions need (someone should KNOW something) → memory. If it is an adjudication (someone DECIDED something) → decision bead via `record-decision`. The `remember-this` skill implements this routing and is the preferred entry point.

---

## Pillar 4 — Old/stale bead removal (BP4.x)

- **BP4.1 Removal means close-with-reason, never delete.** Reaping an old useless bead is a `bd close` with an explicit reason naming the BP4.2 criterion met. Bead deletion (`bd delete`) is reserved for accidental creations within the same session; history is otherwise preserved.
- **BP4.2 Definition of an old useless bead.** A bead is old-useless iff it meets at least ONE of:
  - **(a) Orphaned step bead** from an old build-basic run: titled "Finalize workflow", "Write implementation plan", "Create task beads", "Step spec for...", or similar convoy-remnant boilerplate, with no active parent convoy and no actionable acceptance criteria.
  - **(b) Superseded bead**: explicitly marked superseded by a newer bead, or whose scope was demonstrably absorbed into another bead (close reason must name the absorbing bead ID).
  - **(c) Duplicate bead**: verbatim or near-verbatim title+description duplicate of another OPEN bead (close reason names the surviving bead ID).
  - **(d) Ghost bead**: no title, no description, no assignee, no dependencies, and creation date more than 60 days ago.
- **BP4.3 The reaper sweep protocol.** A reaper sweep (manual or skill-driven) proceeds: (1) enumerate candidates per BP4.2; (2) filter out every BP4.4 protection; (3) close each survivor with a reason citing the criterion and any cross-referenced bead ID; (4) report the reaped list — IDs, titles, criteria — in the session handoff. Sweeps never run silently.
- **BP4.4 What can never be reaped.** The following are excluded from any sweep regardless of age or appearance:
  - **(a)** Beads labeled `[RESEARCH_JOURNAL]` or `[MATH_RESEARCH]` (B3.7, BP2.x).
  - **(b)** BLOCKED beads — they may be waiting on something real; a blocked bead is triaged, not reaped.
  - **(c)** Any bead the human adjudicator has personally touched, claimed, or commented on.
  - **(d)** Decision beads (`type: decision`) — adjudication history is permanent (B2.2).
- **BP4.5 Doubt defers.** If a sweep cannot mechanically establish a BP4.2 criterion (e.g., "is this really superseded?"), the bead is left open and surfaced to the human adjudicator with a **defer** verdict rather than closed.

---

# Mathematical Items Lifecycle System (Pillars 5–9)

Pillars 5–9 govern the four mathematical item kinds — **research beads**
(`[MATH_RESEARCH]`), **literature reviews** (`[LIT_REVIEW]`), **LaTeX beads**
(`[LATEX]` / covered-`.tex` work), and **claim beads** (`[MATH_CLAIM]`) — from
creation through the terminal states, and how each kind routes through the
classifier (catch-no-brainer / full brief pipeline / direct dispatch). The
design goal is stated once, up front:

> **Research must never get spiked.** "Spiked" means either (a) mistyped as a
> `spike` bead and time-boxed to death (BP1.4), or (b) silently dying — no
> progress, no CLOSED, no ARCHIVED, just staleness. Every rule in Pillar 5
> exists to make one of those two failure modes mechanically detectable.

Field precedent: bead `he-66vr` (hecke rig) is the reference instance of the
interim ARCHIVED protocol — labels `archived-research`, metadata
`lifecycle: archived` + `research_ledger: docs/research-ledger/...`, notes
prefixed `ARCHIVED <date>:`, protected via defer. BP5.2 codifies exactly that
shape.

---

## Pillar 5 — Research bead lifecycle & anti-spike (BP5.x)

- **BP5.1 Every math item bead declares a lifecycle state in metadata.** The
  bd metadata key is `lifecycle`, with values `active | parked | archived`.
  A `[MATH_RESEARCH]`, `[LIT_REVIEW]`, or `[MATH_CLAIM]` bead with no
  `lifecycle` key is treated as `active`. State transitions are always
  explicit (BP5.3) and recorded in bead notes with a date.
- **BP5.2 The ARCHIVED state gap and the interim protocol.** bd has no
  first-class state between OPEN and CLOSED, but research journals need one:
  they are not actionable as tasks right now, yet they are not done and must
  never be destructively closed (B3.7, BP2.3). Until upstream bd ships a
  first-class ARCHIVED status (feature request tracked as a brief-system open
  item), the **interim ARCHIVED protocol** is, in full (he-66vr precedent):
  - (a) label `[RESEARCH_JOURNAL]` (legacy label `archived-research` is
    recognized by checkers but new beads use `[RESEARCH_JOURNAL]`);
  - (b) `bd defer <id> --reason="research journal — ARCHIVED-equivalent, do not close"`
    so the bead leaves `bd ready` but stays in `bd list`;
  - (c) metadata `lifecycle: archived`;
  - (d) when the journal content is mirrored to a durable file, metadata
    `research_ledger: <repo-relative path>` (e.g.
    `docs/research-ledger/gamma0-repair-335.md`);
  - (e) a bead note prefixed `ARCHIVED <date>:` stating why it is a journal
    and where the content lives.
  A bead satisfying only part of (a)–(c) is malformed-archived and gets a
  **revise** verdict from `check-math-bead-hygiene`.
- **BP5.3 Anti-spike invariant: no silent death.** A math research bead may
  leave the active flow only through one of three explicit transitions:
  - **close** — the work product is absorbed into a durable home (notes-tier
    LaTeX, paper, package code) and the close reason names that home;
  - **archive** — the BP5.2 protocol, for permanent-reference journals;
  - **park** — the BP5.5 protocol, for deliberately suspended work.
  A bead that is none of {progressing, closed, archived, parked} for more
  than **30 days** (no note, no next-step activity, no state change) is
  **stalled** — a BP5.3 finding. Stalled beads are surfaced as **revise** in
  the hygiene sweep and triaged to the human adjudicator; they are NEVER auto-closed
  (BP4.4a) and never auto-archived. Staleness is a signal to triage, not a
  license to reap.
- **BP5.4 Every active research bead maintains a live next-step.** An
  `active` `[MATH_RESEARCH]` bead must have, at all times, at least one of:
  - an OPEN, dispatchable child or dep-linked bead representing the next
    concrete action (preferred — this is what actually gets dispatched, per
    BP9.5), or
  - a `next step:` line in its notes updated within the BP5.3 window.
  When the last next-step child closes, the finishing session must either
  mint the next one or transition the parent (close / archive / park). A
  research bead with no next-step and no transition is the canonical
  "quietly dying" shape this pillar exists to catch.
- **BP5.5 Parking is explicit and reviewable.** Suspending research is legal
  but never implicit: set `lifecycle: parked` and
  `bd defer <id> --reason="parked: <why> — review by <YYYY-MM-DD>"`. The
  review date is mandatory; a parked bead with no review date is malformed
  (**revise**). `check-math-bead-hygiene` surfaces parked beads whose review
  date has passed as **defer** items for the human adjudicator (resume / re-park / archive).
- **BP5.6 Progress lands in the bead.** A session that advances a math item
  records the advance in the bead itself — a dated note, an updated
  next-step, a linked artifact, or an update to the `research_ledger` file
  named in metadata. Progress that exists only in a session transcript or a
  scratch file is invisible to the staleness clock and will produce a false
  BP5.3 finding; it has not happened, policy-wise.

---

## Pillar 6 — Literature review beads (BP6.x)

- **BP6.1 One bead per review question, not per paper.** A literature review
  bead is `type: task` with label `[LIT_REVIEW]` (plus `[MATH_RESEARCH]` when
  the review serves ongoing original research and should inherit its
  protections). The title states the question the review answers ("what is
  known about X"), never "read papers".
- **BP6.2 Paper entries are structured.** Each tracked paper appears in the
  bead description or notes as a structured entry:
  `citation-key · locator (arXiv id / DOI / URL) · status · one-line relevance`,
  with `status ∈ {queued, skimmed, read, annotated, cited}`. The set of
  entries IS the reading queue.
- **BP6.3 Deep reads atomize; skims stay bundled.** A paper that needs
  detailed working-through (reproducing a proof, extracting a technique)
  gets its own child task naming the paper and the specific extraction
  question; it becomes a BP5.4 next-step of the review bead. Skim-level
  tracking never atomizes — a bead-per-skim is noise.
- **BP6.4 Terminal state is journal, not close-and-lose.** A completed
  review with permanent reference value takes the BP2.2 → BP5.2 archive
  transition. Before a review bead may leave `active`: citations destined
  for a paper must land in the rig's bibliography / notes-tier (the
  `check-citations` surface), and standalone persistent facts route per
  BP3.4. A lit-review bead closed with its findings nowhere durable is a
  BP2.5-analogue violation.
- **BP6.5 The reading queue lives in the bead.** Not in `bd remember`, not
  in a markdown TODO file, not in a transcript (cross-ref BP3.1). Queue
  reshuffles are note updates and count as BP5.6 progress.

---

## Pillar 7 — LaTeX beads (BP7.x)

> Scope note: the `LX` prefix (`subdomains/latex/POLICY.md`, registered
> 2026-07-12, file not yet written) will own detailed LaTeX-workflow rules.
> BP7 covers only the BEAD side — what makes a LaTeX bead well-formed and
> when to atomize. On conflict once LX is adopted, LX wins for LaTeX
> mechanics; BP wins for bead lifecycle.

- **BP7.1 A well-formed LaTeX bead names its targets and declares coverage.**
  It lists the target `.tex` file(s) and states whether each is **covered**
  by the LaTeX HARD GATE (notes-tier scope per he-jwmy: `notes.tex` at any
  depth, anything under `latex/notes/`, or `\input`/`\include`-reachable at
  depth ≤ 2). A LaTeX bead that doesn't say what files it touches or whether
  the gate applies is malformed.
- **BP7.2 Acceptance criteria are gate evidence, not vibes.** A LaTeX bead's
  acceptance criteria must include: compile status via `check-latex`
  (`toolchain-unavailable` honestly reported is acceptable; a faked compile
  result never is), a `check-labels-and-refs` pass for touched labels/refs,
  and a semantic diff summary. For covered files, acceptance additionally
  requires the human adjudicator's approval of the **specific diff** (the hard gate) —
  approval is per-diff, not per-bead.
- **BP7.3 Atomize vs. bundle.** One LaTeX bead = one semantic unit (one
  theorem + its proof + its refs; one section restructure; one notation
  migration). **Atomize** when: edits span sections that are independently
  reviewable, edits target different adjudications, or the change mixes
  covered and uncovered files — never mix coverage classes in one bead;
  split so gate scope is uniform. **Keep bundled** when splitting would
  create intermediate states with dangling refs or a non-compiling document
  — a bead whose midpoint can't pass BP7.2 was atomized too far.
- **BP7.4 LaTeX beads link their mathematical provenance.** A LaTeX bead
  writing up a tracked claim dep-links the `[MATH_CLAIM]` bead (Pillar 8) so
  gate review sees where the mathematics came from and claim status
  (`written-up`) can advance when the diff lands.

---

## Pillar 8 — Mathematical claim beads (BP8.x)

- **BP8.1 One claim bead per tracked claim.** A conjecture, result, or proof
  fragment worth tracking gets its own bead: `type: task` (or `feature` when
  it implies a shippable writeup), label `[MATH_CLAIM]`, with the claim
  stated **verbatim** in the description (LaTeX notation welcome). A vague
  paraphrase is not a claim statement.
- **BP8.2 Claim status is metadata and moves explicitly.** Metadata key
  `claim_status: conjectured | evidence | proved | written-up | refuted`.
  Progression is monotone left-to-right except `refuted`, which may occur
  from any state. Every transition is recorded in notes with a date and an
  evidence pointer (the computation, the proof location, the counterexample).
- **BP8.3 Proved is not done.** A `proved` claim bead stays open until the
  proof is written up in the notes-tier (linked BP7.4 LaTeX bead, or a cited
  notes location). The close reason must point at where the writeup lives.
  Closing a proved-but-unwritten claim is how results evaporate.
- **BP8.4 Refuted claims archive, never delete.** A refutation is a negative
  result and negative results are journal content: set
  `claim_status: refuted`, record the counterexample/contradiction pointer,
  then take the BP5.2 archive transition. Deleting or bare-closing a refuted
  claim destroys exactly the information that prevents re-deriving the dead
  end.
- **BP8.5 Claim dependencies are bead dependencies.** If claim A's proof
  depends on claim B, record it with `bd dep`. A claim marked `proved` while
  depending on a non-`proved` claim is a conditional result and its
  statement must say so explicitly; `check-math-bead-hygiene` flags the
  mismatch as **revise**.

---

## Pillar 9 — Classifier routing for math items (BP9.x)

How mathematical items split across the three dispatch paths:
**catch-no-brainer** (mechanical, the human adjudicator-bypass), the **full brief pipeline**
(brief-prep → adjudication), and **direct dispatch** (sling to a worker, no
brief).

- **BP9.1 Math-content dispositions are never no-brainers.** Any brief whose
  disposition would change mathematical content — the body/notes of a
  `[MATH_RESEARCH]`, `[MATH_CLAIM]`, or `[LIT_REVIEW]` bead, a claim status,
  or any covered `.tex` file — is not compact-eligible and never routes
  through the catch-no-brainer bypass. `catch-no-brainer` must treat these
  as a safety override (same mechanism as its server-touching and
  user-skill-touching overrides): emit `no_brainer:false`,
  `compact_eligible:false`, and route to the full brief pipeline.
- **BP9.2 Covered-`.tex` adjudication is a human hard gate.** Route:
  full-form brief with the `check-latex` evidence block attached (BP7.2).
  Never direct dispatch to merge, never compact form, regardless of how
  small the diff looks (he-jwmy: approval is of the specific diff).
- **BP9.3 Mechanical math-adjacent chores may go catch-no-brainer.**
  Bibliography formatting, label renames carrying a `check-labels-and-refs`
  PASS report, research-ledger file moves, and similar record-keeping are
  no-brainer-eligible PROVIDED the diff touches no covered `.tex`, no claim
  statement, and no research-bead body — evidence attached, standard
  overrides checked first.
- **BP9.4 Direct dispatch is for well-formed atomized work.** A bead may be
  slung directly (no brief) when it has concrete acceptance criteria, writes
  no covered `.tex`, and sits behind no open human gate. Computations
  serving a research bead are the standard case — and when the work is an
  experiment, it passes `is-good-experiment` first (one falsifiable
  question, or no dispatch; results feed the research bead per E7, not the
  void).
- **BP9.5 Research beads are never dispatched as units.** You dispatch a
  research bead's next-step children (BP5.4), never the parent itself. The
  parent is the journal and coordination point; handing a months-scale
  open-ended bead to a time-boxed worker is a category error that produces
  either a fake close or an abandoned claim — both BP5.3 failure shapes.

---

## Verdict vocabulary (shared, per POLICY-POLICY)

| Verdict | Meaning |
| --- | --- |
| **approve** | Current state is compliant; no action required |
| **revise** | Drift found; each item listed with the rule violated and one-line remediation |
| **defer** | A human call is needed; the open question is stated explicitly |

A future `check-bead-policy` skill never emits **reject** (reject applies only to artifacts, not to audits of running state). The same constraint applies to `check-math-bead-hygiene` (the Pillar 5–9 auditor).

---

## Pillar 10 — Dolt Migration Safety (BP10.x)

> **Applies from:** Beads 1.1.0 (303e263fe) — the version that ships the Remote-Migrate Gate.
> Rules below are required by the multi-clone migration protocol Beads 1.1 mandates.
> Added 2026-07-20 via PP2.6 hot-fix path (the human adjudicator Q21); retroactive `new-bead-policy`
> proposal due within 7 days.

**BP10.1 — One migrator per schema version bump.** In any multi-clone setup sharing a dolt remote, exactly ONE clone is designated the migrator for a given schema bump. All other clones must run `bd bootstrap` (not `bd migrate`). Running `bd migrate` on two clones against the same remote in the same version window is a BP10.1 violation.

**BP10.2 — The city rig is the canonical migrator.** The designated migrator is always the city rig (`<city-root>/<repo-name>`). Working copies (`<repos-root>/<repo-name>`), worktrees, and brief-operator instances never run `bd migrate`. The city rig migrates first; everything else bootstraps after the push.

**BP10.3 — Remote-Migrate Gate is required.** Any migration to a remote-backed database requires `BD_ALLOW_REMOTE_MIGRATE=1`. The gate's three auto-outcomes: (a) same version, no drift → proceed automatically; (b) remote already ahead → redirect to `bd bootstrap`; (c) genuine fork → halt and surface to the human adjudicator.

**BP10.4 — Pre-migration backup is mandatory.** Before any `bd migrate` on a rig with a dolt remote: run `bd export --all -o backup-<rig>-$(date +%Y%m%d).jsonl`. No exceptions.

**BP10.5 — Pre-migration sync.** Before running `bd migrate`, the migrator must first complete `bd dolt push && bd dolt pull` to ensure it is working from canonical remote state.

**BP10.6 — Post-migration blocked repair.** After any migration completes: run `bd recompute-blocked` to repair the `is_blocked` flag across the distributed setup.

**BP10.7 — dolt-remotes-patrol gates on reconciliation.** `dolt-remotes-patrol` may only be re-enabled in `city.toml` after ALL three: (a) every registered rig has clean `bd dolt status`; (b) `bd recompute-blocked` run city-wide; (c) reconciliation recorded as a decision bead (the human adjudicator sign-off).

**BP10.8 — Stale-db worktrees are time-limited.** `gt-*-mol-dog-stale-db` worktrees must be reconciled (`bd bootstrap` inside them) or removed within 7 days of the migration that produced them.

**BP10.9 — `bd init` on new clones uses `--init-if-missing`.** New clone initialization uses `bd init --init-if-missing` (Beads 1.1) for idempotency.

---

## Change Log

| Date | Change | Rationale |
| --- | --- | --- |
| 2026-07-20 | Added Pillar 10 (BP10.1–BP10.9): Dolt Migration Safety for Beads 1.1.0 (303e263fe). Governs multi-clone migration protocol introduced by the Remote-Migrate Gate. PP2.6 hot-fix path; retroactive proposal due within 7 days. | the human adjudicator Q21 directive: migration plan for active gsp/agent_skills fork crisis. Full plan: `<city-root>/.beads/decisions-track/77-gt-y1gwuy-beads-migration-plan.md`. Trinity incomplete: `check-beads-policy` / `new-beads-policy` for BP10 not yet scaffolded. |
| 2026-07-12 | Initial draft (BP1–BP4) | the human adjudicator decree: distinguish mathematical research from technical investigation; codify memory routing and old-bead reaping. NOTE: `mathcity/docs/rule-prefix-registry.md` does not yet exist, so the BP prefix is provisionally claimed here pending registry creation (PP5.2). BP2.4 flags a needed B3.7 amendment via `new-brief-policy`. Trinity incomplete: `check-bead-policy` / `new-bead-policy` skills not yet scaffolded (PP1.1). |
| 2026-07-19 | Added Pillar 0 (BP0.1–BP0.6): Pre-creation redundancy gate for dispatch beads. Introduces `new-beads-policy` skill (mathcity.new-beads-policy) as mandatory pre-hook before `mathcity.work` dispatch-bead creation. xkcd-927 is the test; three-verdict system (PROCEED/MERGE/DROP). | the human adjudicator Q19 directive: "pre-hook that checks for redundancy in the set of all beads currently written for dispatch." Filed as gt-hpga8f. |
| 2026-07-12 | Added Pillars 5–9 (BP5–BP9): Mathematical Items Lifecycle System — research-bead anti-spike rules and interim ARCHIVED protocol (BP5, codifying the he-66vr field precedent), literature-review beads (BP6), LaTeX beads and the atomize/bundle rule (BP7), mathematical claim beads with `claim_status` metadata (BP8), classifier routing across catch-no-brainer / brief pipeline / direct dispatch (BP9). Registry note resolved: BP prefix now reserved in `mathcity/docs/rule-prefix-registry.md`. | Outside-agent initial pass at the math-items lifecycle, per the human adjudicator's request: ensure research never gets spiked (mistyped as `spike` OR silently dying with no progress / no CLOSED / no ARCHIVED — the state-gap identified via he-66vr). Companion tools drafted: `check-math-bead-hygiene` (read-only BP5–BP9 auditor) and `new-math-bead-policy` (well-formed math-bead creator) in `<repos-root>/agent-skills/skills/`; these partially satisfy the PP1.1 trinity for the math-item subset — full `check-bead-policy` / `new-bead-policy` still pending. Still Draft; governs nothing until the human adjudicator adopts (PP2.1/PP2.2). BP9.1 flags a needed `catch-no-brainer` safety-override extension. |
