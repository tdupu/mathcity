# City Operations Policy

Parent: [README.md](./README.md)

| Field | Value |
| --- | --- |
| Status | **Draft** — compiled 2026-07-23 from the human adjudicator's city-behavior directives; rules marked **PROPOSED** are Claude suggestions not yet adopted and require a grilling pass |
| Date | 2026-08-15 |
| Decided | the pack owner (directives, 2026-07-23 session); PROPOSED rules pending |
| Applies to | The running Gas City instance: dispatch, scheduling, molecules, formulas, and every rig the city manages |
| Rule prefix | **CT** (City Operations) — reserved in [rule-prefix-registry.md](../../docs/rule-prefix-registry.md); distinct from the Computing domain's `C` prefix |
| Enforced by | `check-city-policy` |
| Amended by | `new-city-policy` |
| Consumers | Mayor priming (`mayor-math`); dispatch formulas and orders; `check-hygiene`-family skills; any agent planning or slinging work |
| Siblings | [POLICY.md](./POLICY.md) (pack portability & boundary, P-rules); `<city-root>/POLICY.md` (dated standing directives); brief-system POLICY.md (B/G-rules) |

System mechanics reference:
[../../docs/TECHNICAL-SPEC.md](../../docs/TECHNICAL-SPEC.md).

Governs how the city **behaves as a factory**: how work is admitted, queued,
dispatched, tracked, interrupted, judged, and cleaned up. The sibling P-rules
govern what the *packs* may look like; these CT-rules govern what the *city
does at runtime*. Every rule has an ID and a pass/fail criterion a skill or
gate can cite.

Rules trace to one of two authorities:

- **Adopted** — direct the human adjudicator directive (2026-07-23 unless noted).
- **PROPOSED** — Claude-suggested extension in the same spirit; treat as
  draft input to a grilling session, not as standing policy.

## Vocabulary

Uses gascity vocabulary throughout (P5.1): a **rig** is a managed repo, a
**formula** is a workflow definition, a **molecule** is a running instance of
a formula, a **bead** is the durable work record, **sling** is dispatch, an
**order** is a scheduled patrol. "The user" is the human adjudicator.

## Source mapping — Gas Town / Gas City principles (check-zero survey)

the human adjudicator selected 13 principles to keep from Steve Yegge's ["Welcome to Gas
Town"](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04) and
["Welcome to Gas City"](https://steve-yegge.medium.com/welcome-to-gas-city-57f564bb3607),
plus flagged a standalone gap (sandboxing). Before adapting each into a rule,
`check-zero` was run against `mathcity/`, `dev/POLICY.md`, `<city-root>/POLICY.md`,
`AGENTS.md`, and `OUTSIDE-AGENTS.md` to avoid duplicating coverage that
already exists under different vocabulary.

| Principle | Verdict | Where |
| --- | --- | --- |
| Physics over politeness (GUPP) | **gap** | new CT1.5 |
| Molecularize work in advance | **covered** | CT3.1, CT6.1 |
| One data plane (beads only) | **covered** | CT10.3 (already PROPOSED) |
| Completion over uptime | **gap** | new CT1.6 |
| Reusable workflow templates | **partial** | CT4.1–CT4.2 cover routing; new CT4.4 covers the write-once/library discipline |
| Graceful degradation | **gap** | new CT11.1–CT11.2 |
| Patrols back off when idle | **gap** | new CT1.7 |
| Never a single agent on a real process | **partial** | CT9.1/CT7.2 cover redundant *review*; new CT9.3 covers redundant *execution* |
| Reliability is a dial | **covered** | CT9.2 (already PROPOSED) |
| Formula library as durable/forkable inventory | **partial** | folded into new CT4.4 |
| Recursive/fractal management | **not yet applicable** | current scale doesn't need it; noted in Open questions, not ruled |
| Foundation, not monolith | **covered** | `dev/POLICY.md` Pillar 2 (ownership boundary) is this principle already, at the pack level |
| Fine-grained model tiering | **covered** | CT8.1–CT8.2 |
| Sandboxing (the human adjudicator-flagged gap) | **confirmed zero coverage** | new Pillar CT12 |

**Prefix note:** rule IDs below use the **CT** prefix (City Operations),
reserved in `mathcity/docs/rule-prefix-registry.md`. An earlier draft used a
bare `C` prefix, which collided with the Computing domain's `C` prefix (a
PP1.5 violation); that collision has been resolved by renumbering the whole
document from `C<n>.<m>` to `CT<n>.<m>`. IDs are now safe to cite elsewhere.

---

## Pillar CT1 — Capacity & queueing

*Every rig has a user-set concurrency target; work waits, it is never lost.*

- **CT1.1 Per-rig concurrency target N(R).** For each rig R there exists a
  number N(R), **set by the user**, giving the desired number of molecules
  running on R at any time. N(R) is declared in city configuration via gc's
  `max_active_sessions` field — the actual substrate knob for bounded
  per-rig concurrency (pool `max` / `max_active_sessions` vs. pack agent
  definition is a placement detail, not an open question about whether the
  mechanism exists), and every formula and
  workflow must be shaped so the running-molecule count on R converges to
  N(R): the city neither idles slots while compatible work is queued, nor
  runs more than N(R) molecules on R. Pass: at steady state with a non-empty
  queue, running molecules on R == N(R). Fail: sustained running count
  above N(R), or sustained idle slots while eligible work waits → **revise**.

- **CT1.2 Dispatched work is never lost — durable queue, immediate promotion.**
  Work slung at a rig whose N(R) slots are full is **enqueued, never
  dropped**: it exists as a bead in the queue state, survives city restarts,
  and the moment a slot frees the next eligible item starts (within one
  scheduler/patrol tick — a bounded, stated latency, not "eventually").
  The bounded tick is a real substrate mechanism: gc's `patrol_interval`
  sets the tick period, `max_wakes_per_tick` caps promotions per tick, and
  `nudge_dispatcher` forces an immediate promotion when a slot frees rather
  than waiting for the next scheduled patrol. The queue is the beads DB,
  not any process's memory. Pass: every sling
  either starts a molecule or produces a queued bead; freed slots are refilled
  within the stated tick bound; `gc start` after a crash resumes the same
  queue. Fail: a sling that returns success with no molecule and no queued
  bead, work found "forgotten" after a restart, or a freed slot that sits
  idle past the tick bound with eligible work queued → **fail** (P6.1: a
  silently dropped sling is a silent failure).

- **CT1.3 (PROPOSED) Backpressure is surfaced, never silently accumulated.**
  The queue has a per-rig depth threshold; crossing it emits a loud signal to
  the user (mail/nudge with depth, oldest-item age, and projected drain time
  at current N(R)) — accumulating hundreds of consumer-less beads in silence
  is the failure mode this rule exists to prevent (origin: 99 `gt-` beads
  with 0 consumer sessions, cf. P1.18). Pass: threshold defined; crossing it
  produces a visible signal naming an escalation target. Fail: queue depth
  or oldest-age growing unboundedly with no signal → **fail** (P6.1).

- **CT1.4 (PROPOSED) No starvation; fairness across rigs.** No queued item
  waits unboundedly while later-arriving work runs: priority is respected,
  but waiting time ages an item's effective priority, and the scheduler does
  not let one rig or one epic monopolize shared resources (operator pools)
  while another rig's queue never drains. Pass: max queue age is bounded and
  monitored. Fail: an item observed starved behind a stream of newer items
  of equal stated priority → **revise**.

- **CT1.5 (PROPOSED) Agents run their hook without waiting to be asked.** An
  agent (or agent-role session) that starts up, resumes, or finishes a step
  and finds further eligible work on its own hook/queue begins it
  immediately, without waiting for a user prompt, nudge, or "go ahead."
  Distinct from CT1.2 (the scheduler's duty to promote queued work into a
  slot): CT1.5 is the agent's own duty, once slotted, to act rather than idle
  waiting for input. (Origin: Gas Town's GUPP — "if there is work on your
  hook, YOU MUST RUN IT," physics over politeness.) Pass: an agent with
  eligible hooked work begins it in the same turn it becomes visible, no
  user turn required. Fail: an agent sits idle with actionable work on its
  hook, waiting for the user to say "go" → **revise**.

- **CT1.6 (PROPOSED) The city optimizes for landing work, not for keeping
  processes alive.** N(R) (CT1.1) describes desired concurrency, not a
  liveness target defended for its own sake: a molecule with nothing left to
  do closes rather than idling to "stay running," and success is measured by
  convoys/epics reaching done, not by session uptime or slot occupancy.
  (Origin: Gas Town/Gas City — Kubernetes asks "is it running?"; Gas Town
  asks "is it done?"; terminal-goal orchestration, not continuous
  desired-state reconciliation.) Pass: closed work is the reported success
  metric (CT5.1); no molecule or session is kept alive past its work being
  done. Fail: sessions or molecules lingering with no eligible work, held
  open to preserve apparent throughput → **revise**.

- **CT1.7 (PROPOSED) Patrols and orders back off when idle, and wake
  instantly on new work.** A patrol/order that finds nothing to do on a pass
  waits longer before its next pass, up to a stated ceiling; any mutating
  `gc`/`bd` command — not just its own schedule — wakes it immediately
  rather than leaving it to poll on the old interval. (Origin: Gas Town's
  patrol pattern — Refinery/Witness/Deacon loops back off when quiet, any
  mutating command wakes the town.) Pass: an idle patrol's poll interval
  grows on repeated empty passes and resets to immediate on a mutating
  event. Fail: a patrol polling a fixed short interval indefinitely
  regardless of load, burning cycles/tokens on empty checks → **revise**.

- **CT1.8 Routed work is conserved until it progresses or is surfaced as
  stuck.** Every bead routed for execution — including formula/order-internal
  step beads carrying `gc.routed_to`, `gc.run_target`, or
  `gc.execution_routed_to` — must reach one of three observable states within
  a bounded time: naturally claimed and progressing; deliberately closed,
  deferred, or blocked with evidence; or surfaced as a stuck/lost-bead signal
  linked to the original bead. Internal formula steps are not noise for this
  rule. Pass: every routed open/in-progress bead has a live claimant,
  intentional non-runnable disposition, or linked stuck/lost classification
  event within the configured bound. Fail: a routed bead remains open or
  in-progress with no live claimant and no stuck/lost signal past the bound
  → **fail**.

## Pillar CT2 — Idempotent & convergent dispatch

*Dispatching twice must cost nothing; superseding instructions converge on
the in-flight work instead of racing it.*

- **CT2.1 Dispatch is idempotent.** Restates and inherits
  [P1.21](./POLICY.md) (pre-sling assignee check; abort loudly on an active
  non-stale assignee; races resolve via `bd update --claim` atomicity;
  post-sling verify-assignee gate stays mandatory). If the same work is
  deployed twice, the city structure guarantees no extra compute and no
  duplicate compute; competing claimants resolve gracefully. This is not a
  gap to build: gc already ships idempotency infrastructure — the
  `idempotent` order field, signed-body-hash dedup, and replay protection —
  which this rule inherits and requires stay on. Pass/fail: as P1.21.

- **CT2.2 Near-duplicate instructions merge at intake.** If nearly identical
  instructions are dispatched twice, the city recognizes the overlap at
  intake and **merges** them: one work item proceeds; the second request is
  recorded by appending a linked bead to the first (P1.19 — append, don't
  edit), any genuinely new constraints from the second phrasing are folded
  into the brief (CT7.1), and the merge is reported visibly ("MERGED with
  <id>"), never swallowed. Pass: duplicate intake yields one running
  molecule, one appended record, one visible merge notice. Fail: two
  molecules doing substantially the same work, or a second request silently
  discarded → **fail**.

- **CT2.3 Supersession converges on in-flight work.** When a command is
  superseded by a newer instruction, the city **finds the related work in
  progress and adjusts the plans accordingly**: locate the affected
  molecules/beads, record the new instruction (`bd supersede` /
  linked bead per P1.19), salvage completed steps that remain valid (CT6.2),
  cancel steps the new instruction obsoletes — loudly, with the delta
  stated — and continue under the revised plan. Pass: after supersession,
  exactly one live plan exists, its delta from the old plan is recorded, and
  no molecule is still executing the obsolete plan. Fail: old and new plans
  running concurrently, or in-flight work discarded wholesale when salvage
  was possible → **revise**.

## Pillar CT3 — Planning structure

*Work arrives as prose; it runs as a dependency graph.*

- **CT3.1 Work is automatically structured as PERT.** Accepted work is
  decomposed into a dependency DAG — tasks with explicit predecessor edges
  (bd dependencies) and per-task estimates — before execution begins.
  Parallelizable tasks are actually parallelized (subject to CT1.1); serial
  chains are explicit, not incidental. Pass: every non-trivial work item's
  bead tree shows tasks + dependency edges before its molecules run. Fail:
  a multi-step job executed as one opaque blob, or dependencies discovered
  mid-flight that decomposition should have surfaced → **revise**.

- **CT3.2 Work is organized into epics.** Every task bead belongs to a parent
  epic (bd type `epic` — P5.3: real types only) grouping the user-level goal;
  epics carry the rollup view CT5 reports on. Pass: no orphan task beads on
  multi-task work. Fail: related tasks with no common epic ancestor →
  **revise**.

- **CT3.3 (PROPOSED) The critical path drives scheduling.** Among eligible
  queued items, the scheduler prefers items on the PERT critical path and
  items that unlock the most blocked successors (the computed
  `unlock_count` must actually be consumed, not just recorded — origin:
  brief-system G8 finding, unlock_count computed-but-unused). Pass:
  tie-breaks among eligible work demonstrably use critical-path/unlock
  ordering. Fail: unlock/critical-path signals computed and ignored →
  **revise**.

- **CT3.4 (PROPOSED) Estimates are recorded and reconciled.** Each PERT task
  carries an estimate (time and/or tokens); at close, actuals are recorded
  next to the estimate. Calibration drift (systematic under/over-estimation)
  is periodically summarized so future PERT charts improve. Pass: closed
  tasks show estimate + actual. Fail: estimates that are write-only
  fiction → **revise**.

## Pillar CT4 — Routing & formula lifecycle

*Work goes to a formula that can do it; missing capability creates a
formula, through the front door.*

- **CT4.1 Work routes to a capable formula.** When the user asks for work, the
  city dispatches it to a formula whose **declared** capability matches the
  work (formula metadata/vars — not vibes). Routing decisions are recorded on
  the bead (which formula, why). Pass: every dispatch names the matched
  formula and the capability match. Fail: work slung at a formula outside its
  declared capability, or routing rationale unrecorded → **revise**.

- **CT4.2 No capable formula ⇒ create one.** If no capable formula exists, the
  city creates a new formula rather than force-fitting an existing one — via
  the sanctioned design path: check-wheel first (P1.20 §E alternatives),
  adversarial review of the design (CT9.1), and the formula lands in the owned
  pack set through normal pack discipline (P-rules). Pass: unroutable work
  produces a formula-creation task with a §E section and review, then routes.
  Fail: unroutable work silently dropped, or a new formula slung into service
  with no design review → **fail**.

- **CT4.3 (PROPOSED) New formulas pass a dress rehearsal before joining
  routing.** A newly created formula runs at least one dogfood/smoke
  execution on a bounded test case, with its artifact judged against its
  brief (CT7), before the router may select it for real work. (Origin: the
  brief-pipeline's dispatch half "never fired end-to-end" while appearing
  configured — untested formulas read as capacity that isn't there.) Pass:
  first real routing of a formula cites its rehearsal run. Fail: a formula
  reachable by the router with zero completed rehearsal runs → **revise**.

- **CT4.4 (PROPOSED) Formulas are written once and reused as a library, not
  authored bespoke per dispatch.** A formula is composed once, versioned
  (commit-tracked, per CT7.3 provenance), and instantiated repeatedly; the
  formula set is a durable, browsable inventory (`README-formulas.md` is the
  existing index) that a router (CT4.1) and a human can search before writing
  a new one-off workflow. Hand-assembling a recurring multi-step job from
  scratch a second time, instead of formularizing it, is a CT4.2 violation in
  spirit even when no technically-new formula was ever "created." (Origin:
  Gas City — "your library of formulas becomes a declarative inventory of
  every business process you've ever automated ... forkable by anyone on
  your team.") Pass: a recurring job's second occurrence routes through a
  named, indexed formula. Fail: the same multi-step job hand-assembled from
  scratch a second time with no formula created → **revise**.

## Pillar CT5 — Observability

*The user can always see what is and is not being worked on.*

- **CT5.1 Total visibility of work state.** At all times the user can
  enumerate, from one place: what is **queued** (and its position), what is
  **in progress** (and on which rig/molecule), what is **blocked** (and on
  what), and what **completed** recently. No work state is discoverable only
  by grepping logs or inspecting process tables. Pass: one command/dashboard
  returns the full queued/in-progress/blocked/done partition, consistent with
  the beads DB. Fail: any running molecule or queued item absent from that
  view → **fail** (invisible work is lost work waiting to happen, CT1.2).

- **CT5.2 Molecules report steps and percentage.** Every molecule declares its
  total step count at start and reports **steps completed / total steps**
  plus a percentage as it runs; the epic rolls these up. "Running" with no
  denominator is not a status. Pass: the CT5.1 view shows x/y (z%) for every
  in-progress molecule. Fail: a molecule in progress with unknown total or
  unreported position → **revise**.

- **CT5.3 (PROPOSED) The waiting-on-you list is explicit.** Everything blocked
  on the user's adjudication (brief verdicts, gate approvals,
  `authorize-git-operation`) appears in one dedicated list, distinct from
  machine-blocked work. The city never blocks on human input silently: within
  one tick of entering a human-blocked state, the item is on the list. Pass:
  human-blocked items enumerated in one place with age. Fail: work discovered
  stalled on an approval nobody surfaced → **fail** (P6.1).

- **CT5.4 (PROPOSED) ETAs derive from the PERT chart.** The CT5.1 view shows,
  per epic, a projected completion derived from remaining critical-path
  estimates (CT3.4) and current N(R) capacity — clearly labeled as an
  estimate. Pass: epics display a derived ETA. Fail: none (advisory rule;
  no fail state until adopted with teeth).

## Pillar CT6 — Interruptibility & salvage

*Stopping work must be cheap; nothing done is thrown away.*

- **CT6.1 Work is interruptible at step boundaries.** Molecules checkpoint at
  PERT-step boundaries: completed steps are durably recorded (artifacts on
  the molecule's branch, status in beads) such that an interruption — user
  stop, supersession (CT2.3), crash, or budget halt (CT8.3) — loses at most the
  current step. Pass: interrupt any molecule; completed steps remain recorded
  and recoverable. Fail: an interruption that loses previously completed
  steps → **fail**.

- **CT6.2 Interrupted work is salvaged, not abandoned.** An interrupted
  molecule leaves: partial artifacts committed on its work branch, a
  **resumption brief** (what's done, what's next, what changed), a released
  claim (no stale assignee — stale-claim gate), and a clean worktree state
  (CT10.1). A later molecule — or the same one resumed — picks up from the
  checkpoint instead of restarting. Pass: post-interrupt, the bead carries a
  resumption brief and the branch carries the partial work; resumption does
  not redo completed steps. Fail: interrupted work leaving a dirty worktree,
  a stuck claim, or requiring a from-scratch redo → **revise**.

## Pillar CT7 — Artifacts & briefs (definition of done)

*Every dispatch returns a thing and the standard for judging the thing.*

- **CT7.1 Every dispatch returns an artifact and a judging brief.** All work
  dispatched returns (a) an **artifact** — the deliverable itself — and (b) a
  **brief** stating the criteria on which that artifact is judged. The
  brief's acceptance criteria are fixed at (or before) dispatch, not
  invented after the artifact exists. A molecule is not done until both
  exist and the judgment has been rendered. Pass: every closed work bead
  links an artifact and a brief with a recorded verdict against the brief's
  criteria. Fail: work closed with no artifact, no brief, or a brief written
  post-hoc to fit the artifact → **fail**.

- **CT7.2 (PROPOSED) The producer is not the judge.** The artifact-vs-brief
  judgment is rendered by an agent other than the one that produced the
  artifact (reviewer independence — same principle as the review-lane
  fanout in build-basic). Self-judgment is permitted only for trivial
  mechanical steps and must be labeled as such. Pass: verdict author ≠
  artifact author on non-trivial work. Fail: unlabeled self-approval →
  **revise**.

- **CT7.3 (PROPOSED) Artifacts carry provenance.** Every artifact records:
  originating bead, formula + version (commit), model(s) used per tier
  (CT8.2), and input references — enough to re-derive or audit it (the
  runtime face of P1.1 replay and P5.4 truth-in-the-code). Pass: artifact
  header/metadata answers "which bead, which formula, which model, from
  what inputs". Fail: an artifact whose origin cannot be reconstructed →
  **revise**.

- **CT7.4 E2E claims require launch provenance and strict result labels.**
  Before an end-to-end test is launched, the test record declares its launch
  surface (`/mathcity.work`, direct `gc sling --formula`, recurring order,
  manual skill, or other), exact command and variables, expected root
  metadata (`gc.formula_name`, `gc.routed_to`, `gc.run_target`,
  `gc.root_bead_id`), expected first runnable step and target pool, natural
  claim bound, and what the run proves and does not prove. Results use only:
  `PASS` (declared path used, metadata matched, natural claim within bound,
  expected output), `PARTIAL` (component logic passed but the declared E2E
  path did not naturally complete), `BLOCKED-SUBSTRATE` (Dolt, supervisor,
  dispatcher, capacity, or similar substrate blocked the run), `INVALID-SPEC`
  (missing/wrong launch provenance or observed launch differed), or `FAIL`
  (declared path ran naturally and produced wrong behavior). Pass: every E2E
  claim carries the predeclared contract and one exact result label. Fail:
  an E2E claim is made from manual force-claims, missing provenance, or
  softer vocabulary such as "basically works" → **revise**.

- **CT7.5 Hygienic issues for lifecycle blockers.** When a live workflow is
  blocked by substrate, lifecycle, deployment, or policy/runtime mismatch
  rather than by the artifact under review, the operator must file or link a
  durable hygienic issue before treating the brief as resolved. The issue must
  name the failed command or lifecycle point, the affected rig or source path,
  and the recovery owner. Pass: every such blocker has a linked issue or bead
  before the operator closes or bypasses the affected workflow. Fail: a
  blocker is treated as resolved only in chat, scratch notes, or an untracked
  terminal transcript → **revise**.

## Pillar CT8 — Resource economy

*Tokens are the city's fuel; spend them where judgment lives.*

- **CT8.1 Work is optimized for token usage.** Formulas and plans are shaped
  to minimize token spend: no recomputation of work already done (CT2), no
  re-reading of unchanged context a checkpoint already summarized, no
  high-tier model invoked where a low tier suffices (CT8.2), and PERT
  decomposition (CT3.1) sized so each molecule carries only the context its
  steps need. Pass: plans state their token-economy choices where
  non-obvious. Fail: demonstrable duplicate compute or context re-ingestion
  a checkpoint should have prevented → **revise**.

- **CT8.2 Model tiering: high plans, low executes.** High-capability models
  are used for planning, design, decomposition, adversarial review, and
  judgment (CT7.2, CT9.1); low-cost models execute well-specified mechanical
  steps. The tier used is recorded per step (feeds CT7.3 provenance and CT3.4
  actuals). Escalation is allowed — a low-tier step that fails its brief
  re-runs on a higher tier — but must be recorded. Pass: step records show
  tier, with planning/review on high and mechanical execution on low. Fail:
  habitual high-tier execution of mechanical steps, or low-tier planning of
  non-trivial work, with no recorded justification → **revise**.

- **CT8.3 (PROPOSED) Budgets and runaway detection.** Every molecule carries a
  token budget (from its CT3.4 estimate); actuals are metered against it. A
  molecule exceeding budget halts **loudly** at the next step boundary
  (CT6.1) with an escalation naming the overrun and the options (raise
  budget / salvage / cancel) — it does not silently keep spending. Epic and
  city-level spend summaries are available on demand. Pass: budgets set,
  metered, and overruns halt with a visible escalation. Fail: a runaway
  molecule discovered only via the provider's bill → **fail** (P6.1).

## Pillar CT9 — Review

*No plan executes on its author's word alone.*

- **CT9.1 All plans are adversarially reviewed.** Every plan is checked by an
  adversarial review agent **before execution**: the reviewer's stance is to
  refute — hunt for root-cause misses (P1.17), capacity violations (CT1),
  idempotency holes (CT2), boundary breaks (P2/P3), silent-failure paths
  (P6.1), and brief-lessness (CT7.1). Verdicts use the standard vocabulary
  (approve / revise / reject / defer). No plan self-approves. Pass: every
  executed plan carries an adversarial review verdict from a non-author
  agent. Fail: a molecule executing an unreviewed or self-approved plan →
  **fail**.

- **CT9.2 (PROPOSED) Review depth scales with blast radius.** Trivial,
  fully-mechanical plans get a single fast adversarial pass; plans touching
  shared contracts, upstream code, or many rigs get the multi-lane fanout.
  The plan states which review tier it requests and why; the reviewer may
  escalate the tier, never de-escalate it. Pass: review tier stated and
  matched to blast radius. Fail: a wide-blast-radius plan slipped through
  the shallow lane → **revise**.

- **CT9.3 (PROPOSED) Non-trivial live-system work is never dispatched to a
  single agent alone.** For work that mutates a real rig, a real Dolt
  database, or anything user-facing (as opposed to the trivial/mechanical
  steps carved out by CT9.2), the city runs at least two agents with
  overlapping responsibility — a producer and an independent checker (CT7.2),
  or two producers whose outputs are reconciled — rather than trusting one
  agent's single pass. This is redundant **execution**, distinct from
  CT7.2/CT9.1's redundant **review**: a lone reviewer catching a lone
  producer's mistake after the fact is CT7.2; this rule is about not staking
  a real-system change on any single agent's uncorroborated run in the
  first place. (Origin: Gas City — "any agent can go temporarily insane...
  always run at least two or three... reliability comes from
  adversarial/consensus structure, not from trusting one model.") Pass:
  non-trivial live-system dispatches name at least two participating
  agents/roles. Fail: a real-system mutation completed and merged on one
  agent's sole, unchecked pass → **revise**.

## Pillar CT10 — Repository hygiene

*Every rig is maintained to research-mathematics standards. No slop.*

- **CT10.1 Clean worktrees and branches, always.** Every repository the city
  touches is kept to research-mathematics publication standard: worktrees
  clean (no stray untracked files, no uncommitted debris left by molecules),
  branches purposeful (named for their bead/epic, short-lived, deleted after
  merge), history coherent (no fixup litter reaching a main branch, commit
  messages per the claude-commit discipline, P5.5 — no false co-authorship).
  Pass: `git status` clean and branch list current on every rig at molecule
  exit and at session close. Fail: molecule exit leaving dirt in a worktree,
  or accumulating merged/dead branches → **fail** — "no slop" is a standing
  bar, not an aspiration.

- **CT10.2 (PROPOSED) Molecule garbage collection.** Every molecule cleans up
  its working directory/worktree on exit — success, failure, or interrupt
  (CT6.2 salvage commits first, then cleans) — and a periodic sweep order
  detects and reports orphaned molecule directories. This is not new
  machinery to build: gc already provides the reaping knobs; the rule
  requires they be **ON** — `auto_reap_closed_bead_worktrees` (worktree
  removed when its bead closes), `auto_prune_worker_dir` (molecule working
  dir pruned on exit), `wisp_gc_interval` (the periodic sweep cadence), and
  `nested_worktree_prune` (nested worktrees swept too). (Origin: ~50 stale
  `gt-*-mol-*` directories observed littering the city root, 2026-07-23 —
  the litter signature of these knobs left off.) Pass: molecule exit leaves
  no orphan directory; the sweep finds zero — or loudly reports what it
  found. Fail: orphan molecule dirs accumulating silently → **fail** (P6.1).

- **CT10.3 (PROPOSED) State lives in beads, not scratch files.** Durable
  city/work state — queues, progress, decisions, memory — lives in the beads
  DB (`bd remember` for knowledge), never in ad-hoc markdown, MEMORY files,
  or a molecule's local scratch (restates the standing bd rule at city
  scope; CT1.2 durability depends on it). Pass: no work state exists only in
  a scratch file. Fail: a queue, progress record, or decision recoverable
  only from a file some molecule happened to write → **revise**.

## Pillar CT11 — Resilience & graceful degradation

*No single component's outage should take down the whole city; the city
keeps working, in a reduced mode, around what's broken.*

- **CT11.1 (PROPOSED) Every worker role functions degraded, not dead, when a
  dependency is down.** If Dolt, a remote compute server, or any other
  single dependency is unreachable, workers that don't need that dependency
  keep working; only the specific capability that depends on the outage is
  blocked, and it is blocked *loudly* (CT5.3-style visible waiting-state),
  not silently. (Origin: Gas Town/Gas City — "every worker role can run
  solo or in groups; the system still functions in a reduced... mode";
  concretely load-bearing here given `<city-root>/CLAUDE.md`'s existing Dolt
  bootstrap/outage protocol.) Pass: a Dolt or server outage narrows
  capability (named, visible) rather than halting all city work. Fail: one
  dependency outage silently stalls unrelated work with no visible signal →
  **fail** (P6.1).

- **CT11.2 (PROPOSED) No role is a single point of failure for the whole
  city's forward progress.** Town-level roles (Mayor-equivalent, patrol
  roles) degrade to a reduced/manual mode rather than freezing all rig-level
  work when they are themselves unavailable; rig-level work does not
  require a live town-level session to keep moving on already-queued items
  (CT1.2). Pass: rig-level molecules continue draining their queues when a
  town-level role is down. Fail: all work city-wide halts because one
  supervisory role's session isn't running → **revise**.

## Pillar CT12 — Sandboxing & environment discipline

*An agent must know the boundary of the ground it's allowed to touch,
before it touches anything.*

Directly requested by the human adjudicator (2026-07-23): repeated observed failures of
agents acting outside their intended sandbox/execution boundary. No existing
mathcity or dev policy addresses this — confirmed by a `check-zero` survey
(zero hits for "sandbox" across `mathcity/`, `dev/POLICY.md`,
`<city-root>/POLICY.md`, `AGENTS.md`, `OUTSIDE-AGENTS.md`) — this pillar is new
ground, not a restatement of an existing rule under different vocabulary.

- **CT12.1 (PROPOSED) An agent states its execution boundary before acting,
  every session.** Before running any command that reads outside the
  current working directory or writes/deletes anywhere, the agent
  identifies which filesystem root(s) it is actually sandboxed to and which
  root(s) merely *look* reachable (e.g., a dual-mount setup where a shell
  tool and a file tool resolve the same logical path to two different
  absolute paths — a failure mode directly observed in the session that
  drafted this rule). Pass: session start (or first mutating action)
  records the resolved sandbox root(s). Fail: a write/delete lands in a
  path the agent had not confirmed was inside its declared boundary →
  **fail**.

- **CT12.2 (PROPOSED) No mutating action outside the declared boundary
  without explicit escalation.** An action that would touch a path, host,
  credential, or service outside the declared sandbox (CT12.1) is not
  attempted silently — it stops and asks, the same way
  `authorize-git-operation` gates irreversible git operations today. This
  generalizes that pattern from git specifically to the sandbox boundary
  generally. Pass: an out-of-boundary action is caught and escalated before
  execution. Fail: an out-of-boundary read/write/network call executes
  without a prior stop-and-ask → **fail**.

- **CT12.3 (PROPOSED) Sandbox violations fail loud, never silent-succeed
  against the wrong target.** If an agent discovers, mid-task, that it has
  been operating against the wrong root (production instead of a worktree,
  the wrong rig, a mount that resolved somewhere unexpected), it stops,
  reports exactly what happened and what it touched, and does not
  "helpfully" continue or quietly self-correct without saying so (P6.1:
  silent failure and silent recovery are both violations here). Pass: a
  discovered-mid-task boundary violation is reported with full detail
  before any further action. Fail: an agent notices a boundary miss and
  keeps going, or fixes it without telling the user → **fail**.

- **CT12.4 (PROPOSED) Sandbox boundary is verified, not assumed, before
  destructive operations.** `rm -rf`-class operations, force-pushes,
  database drops/truncates, and anything targeting Dolt's internal files
  (per `<city-root>/CLAUDE.md`'s explicit `.dolt/` warning) require the agent to
  positively confirm the target path/resource against the declared boundary
  (CT12.1) immediately before acting — not trust that a path "looks right."
  Pass: a destructive op's target is confirmed against the declared boundary
  immediately before execution. Fail: a destructive op fires against an
  unconfirmed or wrong target → **fail**.

---

## Non-negotiables (quick checklist)

- N(R) is the user's number: never exceeded, never ignored while work
  queues (CT1.1).
- No sling is ever lost — queued durably or running, nothing in between
  (CT1.2).
- No routed bead, including internal formula/order steps, remains open with
  no live claimant and no stuck/lost signal past its bound (CT1.8).
- No duplicate compute from duplicate dispatch — pre-sling check, merge at
  intake, converge on supersession (CT2.1–CT2.3 / P1.21).
- No multi-step work without a PERT decomposition under an epic (CT3.1–CT3.2).
- No unroutable work silently dropped — route it or create the formula,
  reviewed (CT4.1–CT4.2).
- No invisible work: full queue/in-progress/blocked view, steps x/y (z%)
  per molecule (CT5.1–CT5.2).
- No interruption that loses completed steps; no abandonment without a
  resumption brief (CT6.1–CT6.2).
- No work closed without artifact + brief + verdict (CT7.1).
- No E2E claim without a predeclared launch surface, natural-claim bound,
  expected metadata, and strict PASS/PARTIAL/BLOCKED-SUBSTRATE/INVALID-SPEC/
  FAIL result label (CT7.4).
- No high-tier tokens on mechanical steps; no low-tier planning; tier
  recorded (CT8.1–CT8.2).
- No plan executes without an adversarial, non-author review (CT9.1); no
  real-system mutation on one agent's uncorroborated pass alone (CT9.3).
- No slop: clean worktrees, purposeful branches, on every rig, at every
  molecule exit (CT10.1).
- No agent sits idle on hooked work waiting for a nudge (CT1.5); no patrol
  polls forever at a fixed rate with nothing to do (CT1.7).
- No dependency outage silently halts unrelated work (CT11.1); no single
  role's absence freezes the whole city (CT11.2).
- No mutating action outside a stated sandbox boundary without stop-and-ask;
  no destructive op against an unconfirmed target (CT12.1–CT12.4).

## Verdict vocabulary

Reuses the standard vocabulary (approve / revise / reject / defer) exactly
as defined in [POLICY.md](./POLICY.md) for plan, artifact, and policy
verdicts — no parallel verdict vocabulary. CT7.4's E2E result labels are
test-outcome labels, not artifact or review verdicts.

## Open questions (for the grilling pass)

1. **Where is N(R) canonically declared?** Today concurrency lives in
   `city.toml` patches (`pool.max`, `max_active_sessions`) — but P1.2 says
   city behavior flows through imports. Candidate: a mathcity-owned config
   fragment that the patch mechanism materializes, keeping city.toml
   hand-edit-free. Needs a decision + migration bead.
2. **What counts as "nearly identical" for CT2.2 intake merging?** Candidate:
   same rig + overlapping file/scope declaration + semantic-similar
   instruction, adjudicated by the intake formula with the merge decision
   recorded; borderline cases → defer to the user rather than guess.
3. **Step-count granularity for CT5.2.** PERT tasks (CT3.1) are the natural
   denominator; needs a convention for molecules whose formula steps and
   PERT tasks differ.
4. **Who staffs the judge (CT7.2) and the adversarial reviewer (CT9.1)?**
   Candidate: review-synthesizer-shaped roles at high tier (CT8.2), distinct
   from the operator pool so capacity pressure can't squeeze out review.
5. **Budget numbers for CT8.3.** Initial per-molecule defaults, and whether
   budgets derive from CT3.4 estimates automatically or are set per epic.
6. **Which PROPOSED rules to adopt, adapt, or reject** — each was written
   to be individually strikeable.
7. **CT-prefix collision — RESOLVED (2026-07-23).** An earlier draft used a
   bare `C` prefix, which the prefix registry already assigns to the Computing
   domain (`subdomains/computing/POLICY.md`) — a PP1.5 violation that blocked
   adoption and made no ID safe to cite. Resolved by reserving the **CT**
   prefix (City Operations) in `mathcity/docs/rule-prefix-registry.md` and
   renumbering every rule ID from `C<n>.<m>` to `CT<n>.<m>`. No open question
   remains here; retained for provenance.
8. **Minimum crew size for CT9.3.** "At least two agents" is stated but not
   sized per work class — does a routine rig-level fix need 2, and does a
   cross-rig or Dolt-touching change need 3, per Gas City's own "two or
   three"? Needs a concrete threshold table.
9. **Does sandboxing (Pillar CT12) need its own trinity?** Given the severity
   the human adjudicator flagged (repeated real incidents) and that it's genuinely new
   ground with zero prior coverage, it may deserve `POLICY-sandboxing.md` +
   `check-sandbox-policy` + `new-sandbox-policy` as a standalone domain
   (new prefix reservation required) rather than living inside
   `POLICY-city.md`. Open for the human adjudicator's call.
10. **Evidence for CT12.** Drafted from the human adjudicator's stated observation ("many
    examples of agents not sandboxing properly") plus one incident directly
    observed in the drafting session (dual-mount path confusion between a
    shell tool and a file tool). If the human adjudicator has specific bead IDs for prior
    sandbox incidents, citing them here would strengthen CT12's origin notes
    the way CT1.3/CT10.2 cite concrete precedents.
11. **Recursive/fractal management — not yet ruled.** Gas City's "build a
    pack to manage packs" principle has no mathcity analogue yet; the
    existing Mayor→Witness/Deacon/Dogs→Polecats/Crew hierarchy already
    embodies it structurally, but nothing states it as a scaling rule
    ("when supervision load grows, add a layer, don't have the human absorb
    it"). Left unruled pending a sense of whether mathcity will hit that
    scale.

## References

- [POLICY.md](./POLICY.md) — P-rules; especially P1.17 (root causes),
  P1.18 (named-session fleet), P1.19 (append-don't-edit), P1.20
  (check-wheel), P1.21 (dispatch idempotency), P6.1 (fail loud)
- `<city-root>/POLICY.md` — dated standing directives (PR pipeline, upstream issues)
- Brief-system POLICY.md (B/G-rules) — the human-adjudication pipeline CT5.3
  surfaces
- Operator-local context files — lane boundaries assumed throughout
- Steve Yegge, ["Welcome to Gas Town"](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04)
  (Jan 2026) — GUPP/physics-over-politeness (CT1.5), completion-over-uptime
  (CT1.6), patrol backoff (CT1.7), graceful degradation (CT11)
- Steve Yegge, ["Welcome to Gas City"](https://steve-yegge.medium.com/welcome-to-gas-city-57f564bb3607)
  (Apr 2026) — formula library discipline (CT4.4), redundant execution (CT9.3),
  reliability-as-a-dial (already reflected in CT9.2)

## Change log

### 2026-08-15 — CT7.5 added: hygienic issues for lifecycle blockers
Added a durable-issue requirement for substrate, lifecycle, deployment, and
policy/runtime mismatch blockers that affect live workflows. Triggered by the
unified brief pipeline design: blockers found while presenting, filtering, or
migrating briefs must become trackable city hygiene work rather than silent
operator memory.

### 2026-07-28 — CT1.8 and CT7.4 added: routed work conservation and E2E launch provenance
Added a runtime conservation invariant for routed beads, including formula/order-internal steps, and required E2E tests to declare launch provenance, natural-claim bounds, and strict result labels before claims are made. Triggered by gt-608un/gt-v0nja direct formula E2E roots leaving gt-gon21/gt-q103k open and unclaimed without an automatic stuck/lost signal.

### 2026-07-23 — Substrate citations for 4 rules (Option B)
Grounded four rules in the real gc substrate field names rather than
leaving them as open design questions (the human adjudicator #23, Option B, approved
2026-07-23): CT1.1 cites `max_active_sessions` for bounded per-rig
concurrency; CT1.2 cites `patrol_interval` + `max_wakes_per_tick` +
`nudge_dispatcher` for the bounded-tick promotion claim; CT2.1 cites the
`idempotent` order field + signed-body-hash dedup + replay protection as
existing idempotency infrastructure; CT10.2 reframed from "build molecule
GC" to "these knobs must be ON" — `auto_reap_closed_bead_worktrees`,
`auto_prune_worker_dir`, `wisp_gc_interval`, `nested_worktree_prune`. No
pass/fail meaning changed.

### 2026-07-23 — Prefix renumber (C → CT) + trinity completion
Resolved the `C`-prefix collision with the Computing domain (Open question 7,
PP1.5) by renumbering every rule ID from `C<n>.<m>` to `CT<n>.<m>` and
reserving the **CT** prefix (City Operations) in
`mathcity/docs/rule-prefix-registry.md`. No rule text or meaning changed —
IDs and prefix references only. Completed the policy trinity (PP1.1) by
adding the header `Enforced by | check-city-policy` / `Amended by |
new-city-policy` rows and creating both skills. human-approved.

### 2026-07-23 — Principles adaptation pass (Gas Town / Gas City)
Added Pillars CT11 (Resilience & graceful degradation) and CT12 (Sandboxing &
environment discipline, the human adjudicator-directed — a confirmed zero-coverage gap);
added CT1.5 (physics over politeness), CT1.6 (completion over uptime), CT1.7
(patrol backoff), CT4.4 (formula library discipline), CT9.3 (redundant
execution). All new rules are PROPOSED, sourced from a `check-zero` survey
of 13 the human adjudicator-selected Gas Town/Gas City principles against existing
mathcity/dev coverage (see "Source mapping" section) — 5 principles were
already covered under existing rule IDs and needed no new text; 1
(recursive/fractal management) was left unruled as not-yet-applicable.
(The `C`-prefix collision this pass carried forward was subsequently
resolved by the 2026-07-23 CT renumber above.)

### 2026-07-23 — Initial compilation
Compiled from the human adjudicator's city-behavior directives (this session): N(R)
capacity targets, lossless queueing, idempotent/superseding dispatch,
PERT+epic structuring, capable-formula routing with formula creation,
total observability with step-percentage progress, interruptible+salvaged
work, artifact+brief per dispatch, token optimization, model tiering,
adversarial plan review, research-math repo hygiene. PROPOSED extensions
added by Claude for grilling: backpressure (CT1.3), anti-starvation (CT1.4),
critical-path scheduling (CT3.3), estimate reconciliation (CT3.4), formula
dress rehearsal (CT4.3), waiting-on-human list (CT5.3), PERT ETAs (CT5.4),
independent judging (CT7.2), provenance (CT7.3), budgets/runaway detection
(CT8.3), tiered review depth (CT9.2), molecule GC (CT10.2), state-in-beads
(CT10.3). Not yet grilled; no rule here is standing policy until adopted.
