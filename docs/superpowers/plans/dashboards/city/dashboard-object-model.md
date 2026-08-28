# MathCity Dashboard — Object Model

**What this is.** A specification of the `mctl` Python API *as we wish it were*.
Every screen in [dashboard-screens.md](./dashboard-screens.md) reads off these
objects. Fixture data in [dashboard-fixtures.md](./dashboard-fixtures.md).

**How to read it.** This is an **ideal-city** spec. It states what should be
true, not what currently is. Where a property is hard or impossible today, that
is a build item, not a reason to weaken the property. The gap between this
document and the running city **is the development plan** — closing it, in
vertical slices, is the work.

**The governing instruction:** the dashboard asks `mctl` for what it wants in
plain terms. Whether that is cheap or expensive to compute is the backend's
problem, not the caller's. `molecule.is_advancing` is a property; how it is
derived is an implementation detail behind it.

---

## Design principles

These constrain every object below. They come from failures that already
happened.

**1. Derived, not reported.** State that matters is computed from evidence, never
self-reported by the component whose health is in question. `step.is_complete` is
derived from whether its declared artifacts exist — not from whether an agent
remembered to close a bead. Self-reported completion fails silently in the
direction that makes healthy work look dead.

**2. Declare intent up front.** A step declares `expected_artifacts` at authoring
time. That is what makes derivation possible, and it is what makes "did this
actually do what it was supposed to?" an answerable question.

**3. Every claim carries its evidence.** Any derived state exposes the inputs
that produced it. `molecule.is_advancing` is accompanied by `molecule.evidence`.
A verdict with no visible basis is an assertion, and the operator's next question
is always *why do you say that*.

**4. Three-valued, never boolean, for anything probed.** Health is
`healthy | degraded | unreachable`, not `True | False`. A boolean collapses
"reachable but quarantined" into one of the other two and manufactures a
confident wrong answer.

**5. Absence is data.** Empty slots, missing timestamps, rigs with nothing
running, steps that produced nothing — all are information and must be
representable. `None` means "there is none," never "we did not look." Where "we
did not look" is the truth, say `Unknown`.

**6. Nothing is synthesized.** No invented timestamps, no zero standing in for
unknown, no average filling a gap.

**7. Lazy by default.** Collections are lazy; bodies, transcripts, and diffs are
fetched on access. A roster read must not become a content read. Every collection
exposes `.count` without materializing its members.

**8. Mutations plan before they act.** Anything that changes the city returns an
`EffectPlan` first. `dry_run=True` is the default.

---

## `City` — the root

```python
city = mctl.city("~/gt")

city.rigs                     # RigCollection — lazy
city.molecules                # MoleculeCollection — ALL molecules, city-wide
city.agents                   # AgentCollection
city.worktrees                # WorktreeCollection
city.events                   # EventStream
city.formulas                 # FormulaCatalog
city.epics / city.convoys     # grouping objects
city.queue                    # Queue — what is waiting, city-wide
city.capacity                 # Capacity — the levers
city.health                   # Health — three-valued
city.usage                    # Usage — accounts and quota
city.uptime                   # UptimeLog — when the city was on and off
city.is_alive                 # Liveness — with evidence, never a bare bool
```

**`city.molecules` is unfiltered by design.** The census is of *all* molecules;
filtering is the caller's decision, not the API's. `is_advancing` is a property
you filter *on*, not a filter baked into the collection.

### `UptimeLog`

Explicitly requested: the city being off is a legitimate explanation for silence,
and without this record an idle city and a dead city are indistinguishable after
the fact.

```python
city.uptime.intervals         # list[UpInterval] — start, end, reason
city.uptime.current           # UpInterval | None
city.uptime.was_up_at(t)      # bool
city.uptime.downtime_since(t) # timedelta
```

`reason` is one of `manual_stop`, `restart`, `crash`, `maintenance`,
`supervisor_bounce`, `unknown`. **`unknown` is a real and expected value** — a
city that stopped without recording why should say so rather than guess.

---

## `Rig`

```python
rig.name / rig.prefix / rig.path
rig.state                     # active | suspended | degraded
rig.degraded_reason           # str | None — never a silently smaller total

rig.molecules / rig.agents / rig.worktrees / rig.beads
rig.queue                     # Queue
rig.capacity                  # Capacity — N(R), running, free
rig.epics / rig.convoys
rig.health                    # Health, rig-scoped
rig.dispatcher                # Agent | None — the control-dispatcher
```

**A degraded rig is always a row.** It appears in `city.rigs` with
`state="degraded"` and a populated `degraded_reason`, never omitted. Any
aggregate computed across rigs exposes `.degraded_rigs` so a short count is
visibly short.

---

## `Molecule`

One execution of one formula. The atomic row of the census.

```python
molecule.id / molecule.rig / molecule.formula / molecule.formula_version
molecule.source_bead          # Bead — what this is work FOR
molecule.root_bead            # Bead — the molecule's own root

molecule.steps                # StepCollection, layered by dependency depth
molecule.progress             # Progress — (completed, total, percent)
molecule.evidence             # Evidence — WHY the predicates answer as they do
molecule.state                # advancing | stalled | stranded | complete | dormant

# Predicates — ask the object directly
molecule.is_complete()
molecule.is_advancing()
molecule.is_stalled()
molecule.is_stranded()
molecule.is_dormant()

molecule.worker               # Agent | None
molecule.worktree             # Worktree | None
molecule.artifact_root        # Path
molecule.branch               # str | None

molecule.why                  # DispatchCause — why does this exist
molecule.timeline             # Timeline — the lifecycle spine
molecule.cost                 # Cost — tokens, wall time, by tier
molecule.budget               # Budget | None
molecule.convoy               # Convoy | None
molecule.epic                 # Epic | None
molecule.eta                  # Estimate | None
```

### `molecule.state` — the five values

| State | Worker | Progress | Meaning |
|---|---|---|---|
| `advancing` | yes | yes | Healthy, including slow |
| `stalled` | yes | no | Worker holds a slot but is blocked — usually a usage limit |
| `stranded` | no | no | Worker gone, claim dangling, nothing will reclaim it |
| `dormant` | no | no | Open by design, terminal steps not reached, not expected to move |
| `complete` | — | — | Terminal step done |

`stranded` and `dormant` look identical from bead state alone. Distinguishing
them is `mctl`'s job, not the caller's — that is exactly the kind of thing this
API exists to absorb.

### Convention: predicates are methods, stored fields are properties

```python
molecule.formula          # property — stored, free
molecule.is_complete()    # method   — derived, may read disk, git, or the store
```

**The parentheses are a warning.** A predicate here can mean checking declared
artifacts on disk, reading a git log, and querying the bead store. A property
that quietly shells out to git is a surprise; a method is not. Every `is_*`
predicate is a method for that reason, and every predicate has a matching
`.evidence` that shows what it looked at.

The caller still says what it wants in plain terms — `molecule.is_complete()` —
and whether that is cheap or expensive stays the backend's problem.

### `DispatchCause` — the "why" column

```python
molecule.why.kind             # order | human_sling | brief_verdict |
                              # commission | retry | supersession
molecule.why.trigger          # the Order, Brief, or Agent responsible
molecule.why.at               # when
molecule.why.chain            # list[DispatchCause] — retries link back
```

**Recorded at dispatch, not inferred later.** "Why is this running" is a
first-class question and the answer must be stored when the answer is known.

---

## `Step` and `Evidence` — the A–E chain

The diagnostic core of the whole model.

```python
step.id / step.title / step.needs / step.layer
step.expected_artifacts       # list[ArtifactSpec] — DECLARED UP FRONT
step.artifacts                # list[Artifact] — what actually exists
step.is_complete              # DERIVED from artifacts, not reported
step.agent                    # Agent | None — who worked it
step.model_tier               # which tier ran it
step.duration                 # timedelta | None
step.evidence                 # Evidence
```

### `Evidence` — five links, in order

Evidence of work is a **sequence**, not a set of alternatives. Each link carries
whether it fired, when, and where that was read from.

```python
evidence.claimed              # A worker took the step        (D)
evidence.agent_active         # The agent is alive on it      (E)
evidence.commit               # A commit landed               (C)
evidence.artifact             # An artifact was written       (B)
evidence.step_closed          # The step bead closed          (A)

evidence.furthest             # how far the chain got
evidence.broken_at            # where it stopped   ← THE DIAGNOSIS
evidence.last_motion_at       # most recent evidence of any kind
evidence.history              # list[EvidenceEvent] — the full log
```

Each link is an `EvidenceLink` with `.fired`, `.at`, `.source`, `.detail`.

**Reading `broken_at`:**

| Chain reaches | Diagnosis |
|---|---|
| `claimed` only | Claimed, but the agent never came alive |
| `claimed, agent_active` | Agent working, producing nothing yet |
| `…, commit` or `…, artifact` | Work exists — healthy in-flight |
| all five | Complete |
| `artifact` but not `step_closed` | Completion recorded late or not at all |

**`evidence.history` is required, not optional.** Without it you know the current
state but not when it last moved, and "when did this last do anything" is the
question that separates a slow molecule from a dead one.

---

## `Agent`

```python
agent.id / agent.name / agent.rig / agent.template / agent.pool
agent.state                   # creating | active | idle | asleep | suspended | closed
agent.model                   # the model in use
agent.provider                # which provider
agent.account                 # WHICH ACCOUNT — explicitly requested
agent.usage                   # Usage — quota remaining on that account

agent.current_step            # Step | None
agent.current_molecule        # Molecule | None
agent.worktree                # Worktree | None
agent.last_active             # datetime
agent.idle_for                # timedelta
agent.limit_state             # none | rolling_window | weekly
agent.transcript              # lazy — never fetched with the roster
agent.claims                  # ClaimHistory — what it has held, and when
```

**`limit_state` is derived, and the distinction is load-bearing.** A
rolling-window stall is fixed by a nudge; a weekly stall cannot be, and nudging
it wastes attention while the slot stays occupied. Both look identical from a
session list, so the API must tell them apart rather than the operator guessing.

---

## `Worktree`

```python
worktree.path / worktree.branch / worktree.rig
worktree.created_by           # Agent — WHO made it
worktree.step                 # Step | None — WHICH step
worktree.molecule             # Molecule | None
worktree.created_at / worktree.last_activity
worktree.commits              # lazy
worktree.is_orphan            # no live session, no open bead
worktree.is_registered        # does git still know about it
worktree.size                 # bytes
worktree.dirty                # uncommitted changes present
worktree.harvestable          # untracked files with apparent value
```

**`created_by` and `step` are the requested additions** — the worktree census is
only useful if you can trace a junk directory back to the agent and step that
made it. `is_orphan` plus `is_registered` separates "abandoned" from "git forgot
about it," which are different problems.

`worktree.url` gives a stable link so a directory can be referenced in an issue or
handed to another agent.

---

## `Event` and `EventStream`

```python
city.events(since=, until=, tier=, kind=, rig=, subject=)

event.at / event.tier / event.kind / event.subject / event.rig
event.detail
event.cause                   # what triggered it
event.response                # list[Event] — what it triggered
event.url
```

**`event.response` is the proof-of-life mechanism.** Events and *responses to
events* are the evidence the city is alive: an order fires and something claims
work; a brief is filed and the shuffle runs. A cause with no response is a
visible break in the chain, and it is far more informative than either event
alone.

**Tiers:** `alarm` · `milestone` · `progress` · `chatter`. Chatter defaults off —
order firings alone run to thousands per day and would drown the stream.

---

## `Health`, `Liveness`, `Capacity`, `Usage`

### `Health` — three-valued throughout

```python
health.data_plane             # healthy | degraded | unreachable
health.data_plane_detail      # latency, endpoint, quarantine state
health.supervisor             # Component
health.fleet_server           # Component
health.dispatchers            # per rig
health.resources              # Resources — flood detection
health.per_rig                # dict[str, Health]
health.probes                 # list[Probe] — each with succeeded/timeout/refused
```

**`Resources` exists because floods are silent.** A leak that pins descriptors to
deleted directories, or a runaway consuming handles, must surface as a first-class
condition rather than as mysterious latency:

```python
resources.file_descriptors    # used, limit, trend
resources.disk                # per rig
resources.flood_conditions    # list[Flood] — what is flooded, since when, growth
```

### `Liveness` — the canary board

**A canary is a piece of machinery that fires on a declared schedule, whose
*silence* is the signal.** The board is the table of them.

It exists because **silence is ambiguous in the worst direction**: a quiet event
stream means the city is idle, or dead, or that emission broke — and the
reassuring reading looks identical to the catastrophic one. Health cannot be
inferred from the absence of bad news, so something must tick even when there is
no work to do.

The recurring orders are already exactly this, and **their expected cadence is
declared in their own definitions** (`interval = "15m"`). So the board is
*generated*, never tuned: no baseline to learn, no threshold to argue about, and
a canary at 16× its declared interval is self-evidently broken to any reader. A
learned baseline would be a new thing that can itself lie.

```python
city.is_alive.verdict         # alive | idle | dead | unknown
city.is_alive.canaries        # list[Canary]
city.is_alive.last_transit    # last bead closed, molecule completed, step closed

canary.name
canary.expected_interval      # DECLARED by the order, not inferred
canary.last_fired
canary.last_outcome           # success | failure | empty  ← see below
canary.overdue_by
canary.healthy                # fresh AND last_outcome != failure
```

**Canaries prove the scheduler is firing; transit proves work is moving.** Both
are needed, and together they disambiguate:

| Canaries | Transit | Verdict |
|---|---|---|
| fresh | fresh | `alive` — working |
| fresh | stale | `idle` — machinery fine, nothing to do |
| stale | — | `dead` — the machinery itself stopped |
| unreadable | — | `unknown` — say so, never guess |

The `idle` row is the point: it is a legitimate state the city should be able to
state out loud, and without canaries it is indistinguishable from death.

**`last_outcome` is required, and it closes a real hole.** A canary firing proves
the order *ran*, not that it *did anything* — an order that fires on schedule and
errors every time still reads fresh. That is the vacuous-pass shape at the
liveness layer: a check that cannot fail looks exactly like a check that passed.
`healthy` therefore requires both freshness **and** a non-failing outcome.

*(Live instance of exactly this: the reaper's recursive query fails on every run
against one rig, escalating repeatedly. Fresh canary, broken machinery.)*

**Expected cadence comes from the order definitions**, so the canary board is
generated rather than tuned. A canary at 16× its declared interval is
self-evidently broken with no baseline to learn.

**`idle` and `dead` must be distinguishable** — fresh canaries with a quiet event
stream means genuinely idle, and that is a state the city should be able to say
out loud.

### `Capacity` — the levers

Requested explicitly: adjust capacity live and watch the city respond.

```python
capacity.target               # N(R)
capacity.running / capacity.free
capacity.pool_desired         # demand-driven — NOT the same as the ceiling
capacity.pool_max             # the ceiling
capacity.utilization

capacity.set_target(n)                # → EffectPlan
capacity.add_agents(n, pool=)         # → EffectPlan
capacity.disable_formula(name)        # → EffectPlan
capacity.enable_formula(name)         # → EffectPlan
capacity.set_priority(bead, p)        # → EffectPlan
```

**`pool_desired` and `pool_max` are separate properties on purpose.** Raising the
ceiling without raising demand changes nothing, and a surface that shows only the
cap makes that invisible — this is a real and repeated source of "I raised the
limit and nothing happened."

**Every lever returns an `EffectPlan`**, and after applying, `plan.observe()`
gives before/after so the effect of pulling it is visible rather than assumed.

## The control surface

The dashboard is a **web interface for the `mctl` API** — reads and writes. Every
mutation follows the same contract: plan, then apply, then observe.

```python
plan = <object>.<action>(...)   # dry_run=True by default — nothing has happened
plan.preconditions              # why it might refuse — a DESIGNED outcome
plan.changes                    # everything it intends to do
plan.blast_radius               # low | medium | high | gated
plan.apply()                    # now it happens
plan.observe()                  # before/after — did it do what it said
```

`plan.observe()` is what makes *"watch how the city changes when you add agents"*
a real feature rather than a hope. It is part of the contract, not a nicety.

### The actions

**Fleet and capacity**

```python
rig.capacity.set_target(n)             # N(R)
rig.capacity.add_agents(n, pool=)
rig.capacity.disable_formula(name)     # / enable_formula
rig.suspend() / rig.resume()

agent.nudge(text=) / agent.wake() / agent.suspend()
agent.reset()                          # fresh session, bead preserved
agent.close()                          # free the slot — the weekly-limit remedy
```

**Work**

```python
bead.sling(formula=, vars=)
bead.set_priority(p) / bead.claim() / bead.release()
bead.close(reason=) / bead.defer(days=, reason=) / bead.reopen()
bead.block_on(other) / bead.unblock()

molecule.redispatch()                  # the strand remedy
molecule.cancel(reason=)
molecule.step(id).retry()
```

**Orders**

```python
order.run_now() / order.disable() / order.enable()
order.set_interval(duration)
```

**Kill switches**

```python
city.auto_merge.engage(authorization=)   # requires a decision bead
city.auto_merge.release(authorization=)
rig.auto_merge.engage(...)
```

### Blast-radius tiers — the safety model

Every action declares a tier, and **the tier decides the interaction**, not the
designer's taste.

| Tier | Interaction | Examples |
|---|---|---|
| **low** | One click, undo offered | nudge, set priority, run an order now |
| **medium** | Effect plan shown, confirm to apply | set N(R), add agents, disable a formula, defer, redispatch |
| **high** | Effect plan **plus typed confirmation** of the target name | suspend a rig, cancel a molecule, close a session, stop the city |
| **gated** | **The dashboard does not perform it.** It prepares the request and hands it to the existing gate | branch delete, worktree removal, push, merge, PR open, tag, bead delete, kill-switch toggle |

**The `gated` tier is the load-bearing one.** These operations already have a
human-approval gate for good reasons that predate this dashboard. A button that
performs them directly is not a feature — it is a hole in an existing control.
The dashboard's job is to make the request *easy to raise*, never to satisfy it
itself.

**Standing prohibitions inherited in full:** nothing here deletes a worktree,
removes a `.repo.git`, closes a `[RESEARCH_JOURNAL]` bead, drops a database, or
touches a data-plane internal file. Not at any tier, not with any confirmation.

### Attribution

Every mutation records who initiated it, from where, with which plan, and what
actually resulted.

```python
action.actor / action.at / action.source        # "dashboard"
action.plan / action.result / action.trace_id
```

**A change made from a browser must be as traceable as one made from a shell.**
`city.events(kind="control")` is the audit stream, and it is the same stream the
ticker reads — a control action is an event like any other, visible to everyone
watching.

### Reachability

**Loopback only.** The safety model above assumes the interface is not routable
and therefore needs no authentication. **If that ever changes, every tier above is
void** and the whole surface needs an authorization model first. This assumption
is load-bearing and must be stated wherever the interface is deployed.

---

### `Usage`

```python
usage.provider / usage.account
usage.window_remaining / usage.weekly_remaining
usage.resets_at
usage.exhausted               # bool
```

Per agent and aggregated per account. "Which account am I burning, and is there
anything left" is a question the dashboard must answer without a shell.

---

## `Queue` — what is not being worked on

```python
queue.ready_unclaimed         # dispatchable now, nothing took it
queue.blocked                 # each with .blocked_on
queue.tail                    # ready, never dispatched, idle past the bound
queue.starved                 # aged behind newer equal-priority work
queue.deferred                # NOT worked on ON PURPOSE, with expiry
queue.next_up                 # ordered as the dispatcher will actually pull
queue.next_up_is_prediction   # bool — label it honestly
queue.eta                     # Estimate | None
queue.depth / queue.oldest_age
```

**`deferred` is separated from the rest deliberately.** Deliberately-not-worked-on
and accidentally-not-worked-on must never share a visual treatment.

**`next_up_is_prediction`** is a required flag. If dispatch order is not
deterministic and exposed, "what's next" is a guess, and a confident wrong answer
is worse than an admitted uncertain one.

---

## `Formula`

```python
formula.name / formula.shape / formula.version / formula.owned
formula.template              # StepGraph — the DAG, as a template
formula.terminal_step
formula.rehearsal / formula.smoke_test
formula.enabled               # toggled by capacity.disable_formula()

formula.invocations(since=)   # usage over time
formula.outcomes              # completed_with_brief | completed_without |
                              # stranded | quarantined | interrupted | budget_halted
formula.failure_by_step       # dict[step_id, count]  ← the useful one
formula.duration_by_step
formula.cost_by_step
formula.tier_by_step
```

**`failure_by_step` rather than a failure rate.** Always-dies-at-step-5 is a
fixable defect; dies-at-random-steps is an environment problem. A single rate
cannot distinguish them, and the fixes differ completely. These four
`*_by_step` dicts are overlays on one DAG layout, not four separate charts.

---

## `Epic` and `Convoy`

```python
epic.title / epic.children / epic.progress / epic.eta

convoy.members / convoy.land_eligible / convoy.open_members
convoy.member_count
```

**A convoy is whatever gascity says it is** — a named graph of beads grouped by
`tracks` dependencies, distinct from workflows. That definition is not ours to
extend, and this API does not add a `kind` taxonomy on top of it.

**The filtering problem is real but it is about population, not meaning.** In
practice ~80% of convoys are single-member and machine-generated, so an
unfiltered list is mostly noise. The dashboard filters on **observable facts** —
`member_count`, title — and any grouping it presents is a **dashboard-side
heuristic, labeled as such**, never an attribute implying gascity structure.
Default view: `member_count > 1`.

---

## Cross-cutting contracts

### Every read carries its envelope

```python
result.diagnostics            # list[Diagnostic] — structured, coded
result.trace_id
result.trust                  # can this be acted on
result.degraded_rigs          # which rigs did not answer
```

`Diagnostic` carries `code`, `severity`, `message`, `policy_ref`,
`data_location`, `suggested_next_command`, and an `actionable` flag. **The
actionable flag is required**: benign findings can outnumber real ones by two
orders of magnitude, and a surface that mixes them trains the operator to ignore
all of them.

### Every mutation plans first

```python
plan = capacity.set_target(6)   # dry run by default
plan.preconditions              # why it might refuse — a DESIGNED outcome
plan.changes
plan.apply()
plan.observe()                  # before/after
```

### Sorting is grouping, not seven screens

```python
city.molecules.by(agent=) / .by(rig=) / .by(formula=) / .by(epic=)
              / .by(convoy=) / .by(order=) / .by(period=)
```

**One dataset, many groupings, all simultaneously available.** Every object
exposes `.url` so any view is linkable, quotable in an issue, and sendable to
another agent.

### Laziness is part of the contract

Collections do not materialize members on access. `.count` never forces a fetch.
Bodies, transcripts, diffs, and commit lists are fetched only when read.
**Requesting everything at once is the failure mode this rule exists to prevent.**
